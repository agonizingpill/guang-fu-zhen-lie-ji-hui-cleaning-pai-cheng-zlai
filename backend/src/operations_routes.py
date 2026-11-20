from fastapi import APIRouter,Depends
from sqlalchemy import select
from .database import session
from .auth import current,editor,admin
from .field_service import require,audit
from .operations_models import WashCrew,WorkPermit,WastewaterRecord,WashSettlement
from .operations_schemas import CrewInput,CrewState,PermitInput,WasteInput,HandoverInput,SettlementInput
from . import permit_service,waste_service,settlement_service
router=APIRouter()
@router.get('/crews')
def crews(u=Depends(current),db=Depends(session)):return db.scalars(select(WashCrew).order_by(WashCrew.id)).all()
@router.post('/crews')
def crew(b:CrewInput,u=Depends(admin),db=Depends(session)):
    row=WashCrew(**b.model_dump());db.add(row);audit(db,u,'登记清洗班组');db.commit();return row
@router.put('/crews/{key}')
def crew_state(key:int,b:CrewState,u=Depends(admin),db=Depends(session)):
    row=require(db,WashCrew,key,True);row.active=b.active;audit(db,u,'变更班组启用');db.commit();return row
@router.get('/permits')
def permits(u=Depends(current),db=Depends(session)):return db.scalars(select(WorkPermit).order_by(WorkPermit.id.desc())).all()
@router.post('/permits')
def permit(b:PermitInput,u=Depends(editor),db=Depends(session)):return permit_service.plan(db,b,u)
@router.post('/permits/{key}/sign')
def permit_sign(key:int,u=Depends(admin),db=Depends(session)):return permit_service.sign(db,key,u)
@router.post('/permits/{key}/void')
def permit_void(key:int,u=Depends(admin),db=Depends(session)):return permit_service.void(db,key,u)
@router.get('/wastewater')
def waste(u=Depends(current),db=Depends(session)):return db.scalars(select(WastewaterRecord).order_by(WastewaterRecord.id.desc())).all()
@router.post('/wastewater')
def record(b:WasteInput,u=Depends(editor),db=Depends(session)):return waste_service.record(db,b,u)
@router.post('/wastewater/{key}/verify')
def verify(key:int,u=Depends(admin),db=Depends(session)):return waste_service.verify(db,key,u)
@router.post('/wastewater/{key}/handover')
def handover(key:int,b:HandoverInput,u=Depends(editor),db=Depends(session)):return waste_service.handover(db,key,b,u)
@router.get('/settlements')
def settlements(u=Depends(current),db=Depends(session)):return db.scalars(select(WashSettlement).order_by(WashSettlement.id.desc())).all()
@router.post('/settlements')
def prepare(b:SettlementInput,u=Depends(editor),db=Depends(session)):return settlement_service.prepare(db,b,u)
@router.post('/settlements/{key}/sign')
def sign(key:int,u=Depends(admin),db=Depends(session)):return settlement_service.sign(db,key,u)

@router.put('/permits/{key}')
def revise_permit(key:int,b:PermitInput,u=Depends(editor),db=Depends(session)):return permit_service.revise(db,key,b,u)
@router.put('/wastewater/{key}')
def revise_waste(key:int,b:WasteInput,u=Depends(editor),db=Depends(session)):return waste_service.revise(db,key,b,u)
