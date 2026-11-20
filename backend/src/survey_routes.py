import os
import redis
from fastapi import APIRouter,Depends
from sqlalchemy import select
from .database import session
from .auth import current,editor
from .models import SoilingSurvey
from .schemas import SurveyInput
from .field_service import record_survey,queue_assessment,require
from .power_model import train_reference
queue=redis.Redis.from_url(os.getenv('REDIS_URL','redis://redis:6379/0'),decode_responses=True)
router=APIRouter()
@router.get('/surveys')
def readings(user=Depends(current),db=Depends(session)):return db.scalars(select(SoilingSurvey).order_by(SoilingSurvey.id.desc())).all()
@router.get('/surveys/{key}')
def reading(key:int,user=Depends(current),db=Depends(session)):return require(db,SoilingSurvey,key)
@router.post('/surveys')
def record(body:SurveyInput,user=Depends(editor),db=Depends(session)):return record_survey(db,body,user)
@router.post('/surveys/{key}/assess')
def assess(key:int,user=Depends(editor),db=Depends(session)):return queue_assessment(db,key,user,queue)
@router.get('/power-reference')
def evidence(user=Depends(current)):return train_reference()[1]
