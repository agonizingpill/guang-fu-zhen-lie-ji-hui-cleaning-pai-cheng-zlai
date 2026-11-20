from fastapi import APIRouter,Depends
from sqlalchemy import select
from .database import session
from .auth import current,editor,admin
from .models import WashMission
from .schemas import MissionInput,WaterRevision,RetestInput
from . import wash_service
router=APIRouter(prefix='/missions')
@router.get('')
def missions(user=Depends(current),db=Depends(session)):return db.scalars(select(WashMission).order_by(WashMission.id.desc())).all()
@router.post('')
def prepare(body:MissionInput,user=Depends(editor),db=Depends(session)):return wash_service.prepare(db,body,user)
@router.put('/{key}')
def revise(key:int,body:WaterRevision,user=Depends(editor),db=Depends(session)):return wash_service.revise(db,key,body,user)
@router.post('/{key}/dispatch')
def dispatch(key:int,user=Depends(admin),db=Depends(session)):return wash_service.dispatch(db,key,user)
@router.post('/{key}/retest')
def retest(key:int,body:RetestInput,user=Depends(editor),db=Depends(session)):return wash_service.retest(db,key,body,user)
@router.post('/{key}/accept')
def accept(key:int,user=Depends(admin),db=Depends(session)):return wash_service.accept(db,key,user)
