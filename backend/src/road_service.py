from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import select,func
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from .operations_models import WashCrew,WorkPermit
from .road_models import LANE_CODE,RoadLane,RoadReservation,RoadClosure,RoadRequest
from .models import WashMission
from .field_service import require,audit
from . import road_model

LOCAL=ZoneInfo('Asia/Shanghai')
HOLD_STATES=('reserved','entered')

def now_local():return datetime.now(LOCAL).replace(tzinfo=None)
def minute_of_day(moment=None):moment=moment or now_local();return moment.hour*60+moment.minute
def today():return now_local().date()

def parse_start(value):
    if isinstance(value,int):return value
    try:
        hour,minute=str(value).strip().split(':');value=int(hour)*60+int(minute)
    except Exception:raise HTTPException(422,'预约起始时间须为 HH:MM')
    if not 0<=value<=1439:raise HTTPException(422,'预约起始时间须在 00:00–23:59 之间')
    return value

def clock(minutes):return f'{minutes//60:02d}:{minutes%60:02d}'

def window(start,minutes):return f'{clock(start)}–{clock(min(start+minutes,1439))}'

def overlaps(a_start,a_minutes,b_start,b_minutes):
    if a_start is None or a_minutes is None or b_start is None or b_minutes is None:return False
    return a_start<b_start+b_minutes and b_start<a_start+a_minutes

def ensure_lane(db):
    lane=db.scalar(select(RoadLane).where(RoadLane.code==LANE_CODE))
    if lane:return lane
    try:
        with db.begin_nested():
            db.add(RoadLane(code=LANE_CODE,status='open'))
        db.flush()
    except IntegrityError:
        pass
    lane=db.scalar(select(RoadLane).where(RoadLane.code==LANE_CODE))
    if not lane:raise HTTPException(409,'便道档案尚未建立，请刷新后重试')
    return lane

def lock_lane(db):
    ensure_lane(db)
    return db.scalar(select(RoadLane).where(RoadLane.code==LANE_CODE).with_for_update().execution_options(populate_existing=True))

def closure_now(db,road_code=LANE_CODE):
    """Confirmed closure whose window covers the current local minute, if any."""
    day=today();minute=minute_of_day()
    rows=db.scalars(select(RoadClosure).where(RoadClosure.road_code==road_code,
        RoadClosure.work_date==day,RoadClosure.state=='confirmed')).all()
    for c in rows:
        if c.start_minute<=minute<c.start_minute+c.minutes:return c
    return None

def lane_status(db):
    return 'closed' if closure_now(db) else 'open'

def replay_result(db,key,action,response=None):
    """Return the first result for a client request key so a retry never books twice."""
    if not key:return None
    row=db.scalar(select(RoadRequest).where(RoadRequest.request_key==key))
    if not row:return None
    if row.action!=action:raise HTTPException(409,'该请求键已用于其他便道操作，请刷新后重试')
    if response is not None:response.headers['X-Idempotent-Replay']='true'
    if row.result_type=='permit':return require(db,WorkPermit,row.result_id)
    if row.result_type=='reservation':return require(db,RoadReservation,row.result_id)
    if row.result_type=='closure':return require(db,RoadClosure,row.result_id)
    return None

def replay_of(db,key,action):
    return replay_result(db,key,action)

def remember(db,key,action,result_type,result_id,user):
    if key:db.add(RoadRequest(request_key=key,action=action,result_type=result_type,result_id=result_id,actor=user.email))

def estimate_for(load_liters,wet_road,supervisor_minutes=None):
    try:return road_model.estimate(load_liters,bool(wet_road),supervisor_minutes)
    except Exception as error:raise HTTPException(422,f'历史车次样本读取失败：{error}')

def _store_estimate(row,estimate):
    row.minutes=estimate['minutes']
    row.estimate_source=estimate['source'] or 'pending'
    row.estimate_basis=estimate['basis']
    row.estimate_evidence=estimate['evidence']

def _reuse_supervisor(row,load,wet):
    """Keep a supervisor's earlier hands-on estimate when nothing about the trip changed."""
    if row.estimate_source!='supervisor' or not row.minutes:return None
    if abs(float(load)-float(row.load_liters))>1e-9 or bool(wet)!=bool(row.wet_road):return None
    return row.minutes

def supervisor_value(user,value):
    """Only a supervisor may override the model with a hands-on estimate."""
    if value is None:return None
    if not user or user.role!='admin':raise HTTPException(403,'历史样本不足时，通行估时只能由主管填写')
    return value

def attach_draft(db,permit,body,user):
    """Create or refresh the draft reservation that belongs to a permit application."""
    mission=require(db,WashMission,permit.mission_id)
    load=body.load_liters if body.load_liters is not None else mission.water_liters
    estimate=estimate_for(load,body.wet_road,supervisor_value(user,body.supervisor_minutes))
    row=db.scalar(select(RoadReservation).where(RoadReservation.permit_id==permit.id))
    if not row:
        row=RoadReservation(permit_id=permit.id,road_code=LANE_CODE,state='draft',load_liters=load)
        db.add(row)
    row.road_code=LANE_CODE;row.work_date=body.work_date;row.start_minute=parse_start(body.road_start)
    row.wet_road=bool(body.wet_road);row.load_liters=load;_store_estimate(row,estimate)
    db.flush()
    return row

def _conflicts(db,work_date,start,minutes,exclude_id=None):
    rows=db.scalars(select(RoadReservation).where(RoadReservation.road_code==LANE_CODE,RoadReservation.work_date==work_date,RoadReservation.state.in_(HOLD_STATES))).all()
    return [r for r in rows if r.id!=exclude_id and overlaps(start,minutes,r.start_minute,r.minutes)]

def _closures(db,work_date,start,minutes):
    rows=db.scalars(select(RoadClosure).where(RoadClosure.road_code==LANE_CODE,RoadClosure.work_date==work_date,RoadClosure.state=='confirmed')).all()
    return [c for c in rows if overlaps(start,minutes,c.start_minute,c.minutes)]

def _crew_conflict(db,permit,work_date,minutes):
    c=require(db,WashCrew,permit.crew_id,True)
    if not c.active:raise HTTPException(409,'许可班组已停用')
    occupied=db.scalar(select(func.coalesce(func.sum(WorkPermit.minutes),0)).where(
        WorkPermit.crew_id==c.id,WorkPermit.work_date==work_date,
        WorkPermit.state.in_(['signed','used']),WorkPermit.id!=permit.id))
    if occupied+minutes>c.max_daily_minutes:raise HTTPException(409,f'{work_date} 班组当日工时容量不足，无法占用 {minutes} 分钟')
    return c

def reserve(db,permit,supervisor_minutes=None):
    """Called under the lane lock at permit signing: check conflicts, then hold the slot."""
    row=db.scalar(select(RoadReservation).where(RoadReservation.permit_id==permit.id).with_for_update())
    if not row:raise HTTPException(409,'许可缺少便道预约草稿，请先修订许可补全预约时段')
    if row.state!='draft':raise HTTPException(409,'该任务便道预约已办理，不能重复占位')
    estimate=estimate_for(row.load_liters,row.wet_road,supervisor_minutes if supervisor_minutes is not None else _reuse_supervisor(row,row.load_liters,row.wet_road))
    if estimate['minutes'] is None:raise HTTPException(409,'历史车次样本不足，签发前须由主管填写便道通行估时')
    if _conflicts(db,row.work_date,row.start_minute,estimate['minutes']):raise HTTPException(409,'该便道时段已被另一班预约占用，同窗口只签发一单')
    if _closures(db,row.work_date,row.start_minute,estimate['minutes']):raise HTTPException(409,'预约时段与已确认封路重叠，请调整时段')
    _store_estimate(row,estimate)
    row.state='reserved'
    return row

def update_draft(db,permit,body,user):
    row=db.scalar(select(RoadReservation).where(RoadReservation.permit_id==permit.id))
    if not row:raise HTTPException(409,'许可缺少便道预约草稿')
    if row.state!='draft':raise HTTPException(409,'签发后预约时段冻结，暂停单请走改约')
    return attach_draft(db,permit,body,user)

def void_reservation(db,permit):
    row=db.scalar(select(RoadReservation).where(RoadReservation.permit_id==permit.id))
    if row and row.state in ('draft','reserved','paused'):row.state='voided'

def confirm_closure(db,body,user):
    lane=lock_lane(db)
    replay=replay_result(db,body.request_key,'road.closure')
    if replay:
        paused=db.scalar(select(func.count()).select_from(RoadReservation).where(RoadReservation.paused_by_closure_id==replay.id))
        return replay,lane,paused
    closure=RoadClosure(road_code=LANE_CODE,work_date=body.work_date,start_minute=parse_start(body.road_start),
        minutes=body.minutes,reason=body.reason.strip(),state='confirmed',confirmed_by=user.email)
    db.add(closure);db.flush()
    rows=db.scalars(select(RoadReservation).where(RoadReservation.road_code==LANE_CODE,
        RoadReservation.work_date==body.work_date,RoadReservation.state=='reserved').with_for_update()).all()
    paused=[r for r in rows if overlaps(r.start_minute,r.minutes,closure.start_minute,closure.minutes)]
    for r in paused:r.state='paused';r.paused_by_closure_id=closure.id
    # Vehicles already inside keep the lane until they exit; only new entries stop.
    lane=lock_lane(db)
    lane.status=lane_status(db);lane.active_closure_id=closure.id
    remember(db,body.request_key,'road.closure','closure',closure.id,user)
    audit(db,user,f'确认北坡便道封路 {body.work_date} {window(closure.start_minute,closure.minutes)}，暂停{len(paused)}个重叠预约')
    return closure,lane,len(paused)

def lift_closure(db,key,user):
    lock_lane(db)
    closure=require(db,RoadClosure,key,True)
    if closure.state!='confirmed':raise HTTPException(409,'该封路已解除，不可重复复通')
    closure.state='lifted';closure.lifted_by=user.email;closure.lifted_at=datetime.utcnow()
    db.flush()
    remaining=db.scalar(select(RoadClosure).where(RoadClosure.road_code==closure.road_code,RoadClosure.state=='confirmed').order_by(RoadClosure.id))
    lane=lock_lane(db)
    lane.status=lane_status(db)
    lane.active_closure_id=remaining.id if remaining else None
    audit(db,user,f'复通北坡便道（封路{key}），暂停预约须改约后重新占位')
    return closure,lane

def enter(db,key,body,user):
    lane=lock_lane(db)
    replay=replay_of(db,getattr(body,'request_key',None),'road.enter')
    if replay:return replay
    row=require(db,RoadReservation,key,True)
    if row.state=='paused':raise HTTPException(409,'预约已因封路暂停，复通后须先改约再进场')
    if row.state!='reserved':raise HTTPException(409,'仅已签发且未进场的预约可办理进场')
    if closure_now(db):raise HTTPException(409,'北坡便道封闭中，车辆不得进场')
    permit=require(db,WorkPermit,row.permit_id)
    if permit.state not in ('signed','used'):raise HTTPException(409,'许可尚未签发或已撤销，不能进场')
    inside=db.scalar(select(RoadReservation).where(RoadReservation.road_code==LANE_CODE,RoadReservation.state=='entered'))
    if inside:raise HTTPException(409,'前车尚未出场，后车须按预约时段等待便道腾空')
    if row.work_date!=today():raise HTTPException(409,'仅预约当日可办理进场')
    now=now_local()
    if minute_of_day(now)<row.start_minute:raise HTTPException(409,f'未到预约时段，预计 {clock(row.start_minute)} 起进场')
    if _closures(db,row.work_date,minute_of_day(now),1):raise HTTPException(409,'当前时段仍在封路窗口内，不能进场')
    row.state='entered';row.entered_at=datetime.utcnow()
    remember(db,getattr(body,'request_key',None),'road.enter','reservation',row.id,user)
    audit(db,user,f'北坡便道进场 预约{key}（WASH-{permit.mission_id}）')
    return row

def exit_lane(db,key,body,user):
    lock_lane(db)
    replay=replay_of(db,getattr(body,'request_key',None),'road.exit')
    if replay:return replay
    row=require(db,RoadReservation,key,True)
    if row.state!='entered':raise HTTPException(409,'该预约当前不在便道内，不能办理出场')
    now=now_local();end=(row.start_minute+(row.minutes or 0))
    row.overtime_minutes=max(0,minute_of_day(now)-end)
    row.exited_at=datetime.utcnow();row.state='exited'
    permit=require(db,WorkPermit,row.permit_id)
    remember(db,getattr(body,'request_key',None),'road.exit','reservation',row.id,user)
    audit(db,user,f'北坡便道出场 预约{key}（WASH-{permit.mission_id}），超时{row.overtime_minutes}分钟')
    return row

def reschedule(db,key,body,user):
    lane=lock_lane(db)
    replay=replay_of(db,body.request_key,'road.reschedule')
    if replay:return replay
    row=require(db,RoadReservation,key,True)
    if row.state not in ('paused','reserved'):raise HTTPException(409,'仅未进场的预约可改约')
    if row.state=='paused':
        pausing=require(db,RoadClosure,row.paused_by_closure_id) if row.paused_by_closure_id else None
        if not pausing or pausing.state!='lifted':raise HTTPException(409,'便道尚未复通，暂停预约暂不能改约')
    permit=require(db,WorkPermit,row.permit_id,True)
    if permit.state not in ('signed','used'):raise HTTPException(409,'许可已撤销或派工前失效，不能改约')
    load=body.load_liters if body.load_liters is not None else row.load_liters
    wet=row.wet_road if body.wet_road is None else bool(body.wet_road)
    supplied=supervisor_value(user,body.supervisor_minutes)
    if supplied is None:supplied=_reuse_supervisor(row,load,wet)
    estimate=estimate_for(load,wet,supplied)
    if estimate['minutes'] is None:raise HTTPException(409,'历史车次样本不足，改约须由主管填写通行估时')
    start=parse_start(body.road_start)
    if _conflicts(db,body.work_date,start,estimate['minutes'],exclude_id=row.id):raise HTTPException(409,'目标时段已被占用，请另选时段')
    if _closures(db,body.work_date,start,estimate['minutes']):raise HTTPException(409,'目标时段与已确认封路重叠，请另选时段')
    _crew_conflict(db,permit,body.work_date,permit.minutes)
    permit.work_date=body.work_date
    row.work_date=body.work_date;row.start_minute=start;row.load_liters=load;row.wet_road=wet
    row.state='reserved';row.paused_by_closure_id=None;row.reschedule_count=(row.reschedule_count or 0)+1
    _store_estimate(row,estimate)
    remember(db,body.request_key,'road.reschedule','reservation',row.id,user)
    audit(db,user,f'北坡便道改约 预约{key} → {body.work_date} {window(start,estimate["minutes"])}')
    return row
