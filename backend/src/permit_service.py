from sqlalchemy import select,func
from fastapi import HTTPException
from .models import WashMission
from .operations_models import WashCrew,WorkPermit
from .field_service import require,audit

def plan(db,b,u):
    m=require(db,WashMission,b.mission_id,True)
    if m.status!='draft':raise HTTPException(409,'仅草稿清洗任务可申请作业许可')
    c=require(db,WashCrew,b.crew_id)
    if not c.active:raise HTTPException(409,'班组已停用')
    if db.scalar(select(WorkPermit).where(WorkPermit.mission_id==m.id)):raise HTTPException(409,'任务已有许可，不得重复申请')
    p=WorkPermit(**b.model_dump());db.add(p);audit(db,u,f'申请清洗许可 任务{m.id}');db.commit();return p

def sign(db,key,u):
    ref=require(db,WorkPermit,key);mission_id=ref.mission_id
    m=require(db,WashMission,mission_id,True);p=require(db,WorkPermit,key,True)
    c=require(db,WashCrew,p.crew_id,True)
    if p.state!='draft' or m.status!='draft':raise HTTPException(409,'仅未派工草稿许可可签发')
    if not c.active or not p.isolation or p.wind_mps>10:raise HTTPException(409,'班组须启用，完成电气隔离且阵风不得超过10m/s')
    # Crew row serializes capacity changes; READ COMMITTED observes the preceding signer.
    occupied=db.scalar(select(func.coalesce(func.sum(WorkPermit.minutes),0)).where(WorkPermit.crew_id==c.id,WorkPermit.work_date==p.work_date,WorkPermit.state.in_(['signed','used'])))
    if occupied+p.minutes>c.max_daily_minutes:raise HTTPException(409,'班组当日工时容量不足')
    p.state='signed';p.signed_by=u.email;audit(db,u,f'签发许可{key} 占用{p.minutes}分钟');db.commit();return p

def void(db,key,u):
    ref=require(db,WorkPermit,key);mission_id=ref.mission_id
    m=require(db,WashMission,mission_id,True);p=require(db,WorkPermit,key,True)
    if p.state not in ['draft','signed'] or m.status!='draft':raise HTTPException(409,'仅未派工许可可撤销')
    p.state='void';audit(db,u,f'撤销许可{key}');db.commit();return p

def dispatch_guard(db,mission):
    p=db.scalar(select(WorkPermit).where(WorkPermit.mission_id==mission.id).with_for_update())
    if not p or p.state!='signed':raise HTTPException(409,'派工前须主管签发班组作业许可')
    c=require(db,WashCrew,p.crew_id,True)
    if not c.active:raise HTTPException(409,'许可班组已停用，请恢复后派工')
    p.state='used'


def revise(db,key,b,u):
    ref=require(db,WorkPermit,key);mission_id=ref.mission_id
    m=require(db,WashMission,mission_id,True);p=require(db,WorkPermit,key,True)
    if p.state!='draft' or m.status!='draft':raise HTTPException(409,'仅未签草稿许可可修订')
    if b.mission_id!=m.id:raise HTTPException(409,'不可更换许可关联任务')
    c=require(db,WashCrew,b.crew_id)
    if not c.active:raise HTTPException(409,'班组已停用')
    for k,v in b.model_dump().items():setattr(p,k,v)
    audit(db,u,f'修订作业许可{key}');db.commit();return p
