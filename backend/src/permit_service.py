from sqlalchemy import select,func
from fastapi import HTTPException
from .models import WashMission
from .operations_models import WashCrew,WorkPermit
from .road_models import RoadReservation
from .field_service import require,audit
from . import road_service

def plan(db,b,u):
    road_service.lock_lane(db)
    replay=road_service.replay_result(db,b.request_key,'permit.plan')
    if replay:return replay
    m=require(db,WashMission,b.mission_id,True)
    if m.status!='draft':raise HTTPException(409,'仅草稿清洗任务可申请作业许可')
    c=require(db,WashCrew,b.crew_id)
    if not c.active:raise HTTPException(409,'班组已停用')
    if db.scalar(select(WorkPermit).where(WorkPermit.mission_id==m.id)):raise HTTPException(409,'任务已有许可，不得重复申请')
    p=WorkPermit(mission_id=b.mission_id,crew_id=b.crew_id,work_date=b.work_date,minutes=b.minutes,
        wind_mps=b.wind_mps,isolation=b.isolation)
    db.add(p);db.flush()
    road_service.attach_draft(db,p,b,u)
    road_service.remember(db,b.request_key,'permit.plan','permit',p.id,u)
    audit(db,u,f'申请清洗许可 任务{m.id}，便道预约 {b.work_date} {b.road_start}')
    db.commit();return p

def sign(db,key,body,u):
    road_service.lock_lane(db)
    replay=road_service.replay_result(db,body.request_key,'permit.sign')
    if replay:return replay
    p=require(db,WorkPermit,key,True)
    m=require(db,WashMission,p.mission_id)
    c=require(db,WashCrew,p.crew_id,True)
    if p.state!='draft' or m.status!='draft':raise HTTPException(409,'仅未派工草稿许可可签发')
    if not c.active or not p.isolation or p.wind_mps>10:raise HTTPException(409,'班组须启用，完成电气隔离且阵风不得超过10m/s')
    occupied=db.scalar(select(func.coalesce(func.sum(WorkPermit.minutes),0)).where(WorkPermit.crew_id==c.id,WorkPermit.work_date==p.work_date,WorkPermit.state.in_(['signed','used'])))
    if occupied+p.minutes>c.max_daily_minutes:raise HTTPException(409,'班组当日工时容量不足')
    road_service.reserve(db,p,road_service.supervisor_value(u,body.supervisor_minutes))
    p.state='signed';p.signed_by=u.email
    road_service.remember(db,body.request_key,'permit.sign','permit',p.id,u)
    audit(db,u,f'签发许可{key} 占用{p.minutes}分钟，便道时段已占位')
    db.commit();return p

def void(db,key,u):
    road_service.lock_lane(db)
    p=require(db,WorkPermit,key,True)
    m=require(db,WashMission,p.mission_id)
    if p.state not in ['draft','signed'] or m.status!='draft':raise HTTPException(409,'仅未派工许可可撤销')
    road=db.scalar(select(RoadReservation).where(RoadReservation.permit_id==p.id))
    if road and road.state=='entered':raise HTTPException(409,'车辆仍在便道内，须出场后再撤销许可')
    p.state='void';road_service.void_reservation(db,p)
    audit(db,u,f'撤销许可{key}，便道预约位已释放');db.commit();return p

def dispatch_guard(db,mission):
    p=db.scalar(select(WorkPermit).where(WorkPermit.mission_id==mission.id).with_for_update())
    if not p or p.state!='signed':raise HTTPException(409,'派工前须主管签发班组作业许可')
    c=require(db,WashCrew,p.crew_id,True)
    if not c.active:raise HTTPException(409,'许可班组已停用，请恢复后派工')
    road=db.scalar(select(RoadReservation).where(RoadReservation.permit_id==p.id))
    if not road or road.state not in ('reserved','entered','exited'):raise HTTPException(409,'便道预约已暂停或释放，派工前须先改约占位')
    p.state='used'

def revise(db,key,b,u):
    road_service.lock_lane(db)
    p=require(db,WorkPermit,key,True)
    m=require(db,WashMission,p.mission_id)
    if p.state!='draft' or m.status!='draft':raise HTTPException(409,'仅未签草稿许可可修订')
    if b.mission_id!=m.id:raise HTTPException(409,'不可更换许可关联任务')
    c=require(db,WashCrew,b.crew_id)
    if not c.active:raise HTTPException(409,'班组已停用')
    for k in ('crew_id','work_date','minutes','wind_mps','isolation'):setattr(p,k,getattr(b,k))
    road_service.update_draft(db,p,b,u)
    audit(db,u,f'修订作业许可{key}及便道预约');db.commit();return p
