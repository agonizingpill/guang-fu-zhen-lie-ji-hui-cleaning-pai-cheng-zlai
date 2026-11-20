from sqlalchemy import select
from fastapi import HTTPException
from .models import WashMission
from .operations_models import WastewaterRecord
from .field_service import require,audit

def record(db,b,u):
    m=require(db,WashMission,b.mission_id,True)
    if m.status!='accepted':raise HTTPException(409,'仅增益验收任务可登记废水')
    if b.recovered_liters>m.water_liters:raise HTTPException(409,'回收水量不得超过该任务用水')
    if db.scalar(select(WastewaterRecord).where(WastewaterRecord.mission_id==m.id)):raise HTTPException(409,'任务已有废水交接凭据')
    d=WastewaterRecord(**b.model_dump(),used_liters=m.water_liters,recovery_pct=round(100*b.recovered_liters/m.water_liters,4))
    db.add(d);audit(db,u,f'登记废水 任务{m.id} 回收{b.recovered_liters}L');db.commit();return d

def verify(db,key,u):
    d=require(db,WastewaterRecord,key,True)
    if d.state!='recorded':raise HTTPException(409,'仅待核验废水可复核')
    if d.recovery_pct<70 and len(d.low_recovery_reason.strip())<5:raise HTTPException(409,'回收不足70%，须说明渗漏或蒸发等原因（至少5字）')
    d.state='verified';d.verified_by=u.email;audit(db,u,f'核验废水{key} 回收率{d.recovery_pct}%');db.commit();return d

def handover(db,key,b,u):
    d=require(db,WastewaterRecord,key,True)
    if d.state!='verified':raise HTTPException(409,'须先主管核验，交接签收不得重复')
    if len(b.received_by.strip())<2 or len(b.receipt.strip())<5:raise HTTPException(409,'签收人及接收凭证不能为空')
    d.received_by=b.received_by.strip();d.receipt=b.receipt.strip();d.state='handed_over';audit(db,u,f'废水去向交接{key}');db.commit();return d


def revise(db,key,b,u):
    d=require(db,WastewaterRecord,key,True)
    if d.state!='recorded':raise HTTPException(409,'核验后废水凭据冻结')
    if b.mission_id!=d.mission_id:raise HTTPException(409,'不可更换关联任务')
    if b.recovered_liters>d.used_liters:raise HTTPException(409,'回收量不得超过原用水')
    for k,v in b.model_dump().items():setattr(d,k,v)
    d.recovery_pct=round(100*d.recovered_liters/d.used_liters,4)
    audit(db,u,f'补正废水{key}');db.commit();return d
