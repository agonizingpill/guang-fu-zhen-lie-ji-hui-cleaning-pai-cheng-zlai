from fastapi import APIRouter,Depends
from sqlalchemy import select
from .database import session
from .auth import current,editor,admin
from .revisit_models import WaterDelivery,FollowupSurvey
from .revisit_schemas import DeliveryInput,ReceiveInput,FollowupInput,CloseInput
from . import water_service,followup_service
router=APIRouter()
@router.get('/deliveries')
def deliveries(user=Depends(current),db=Depends(session)):return db.scalars(select(WaterDelivery).order_by(WaterDelivery.id.desc())).all()
@router.post('/deliveries')
def plan(body:DeliveryInput,user=Depends(editor),db=Depends(session)):return water_service.plan(db,body,user)
@router.post('/deliveries/{key}/receive')
def receive(key:int,body:ReceiveInput,user=Depends(editor),db=Depends(session)):return water_service.receive(db,key,body,user)
@router.post('/deliveries/{key}/credit')
def credit(key:int,user=Depends(admin),db=Depends(session)):return water_service.credit(db,key,user)
@router.get('/followups')
def followups(user=Depends(current),db=Depends(session)):return db.scalars(select(FollowupSurvey).order_by(FollowupSurvey.id.desc())).all()
@router.post('/followups')
def followup(body:FollowupInput,user=Depends(editor),db=Depends(session)):return followup_service.survey(db,body,user)
@router.post('/followups/{key}/close')
def close(key:int,body:CloseInput,user=Depends(admin),db=Depends(session)):return followup_service.close(db,key,body,user)
