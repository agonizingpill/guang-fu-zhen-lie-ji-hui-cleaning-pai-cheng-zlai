from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from .database import session
from .auth import current,editor,admin
from .road_models import LANE_CODE,LANE_NAME,RoadLane,RoadReservation,RoadClosure
from .road_schemas import EstimateInput,ClosureInput,RoadActionInput,RescheduleInput
from . import road_service,road_model
router=APIRouter(prefix='/road')

def payload(lane,closure=None,paused_count=0):
    return {'lane_code':LANE_CODE,'lane':lane,'closure':closure,'paused_count':paused_count}

@router.get('')
def board(u=Depends(current),db=Depends(session)):
    lane=db.scalar(select(RoadLane).where(RoadLane.code==LANE_CODE))
    reservations=db.scalars(select(RoadReservation).order_by(RoadReservation.work_date,RoadReservation.start_minute)).all()
    closures=db.scalars(select(RoadClosure).order_by(RoadClosure.id.desc())).all()
    # The stored flag records the last confirmed closure; the board shows the
    # closure that actually covers the current local minute.
    current=road_service.closure_now(db)
    status='closed' if current else 'open'
    return {'lane':{'code':LANE_CODE,'name':LANE_NAME,'status':status,'active_closure_id':current.id if current else None},
        'reservations':reservations,'closures':closures,'estimate_model':road_model.summary(),
        'server_date':road_service.today().isoformat(),'server_minute':road_service.minute_of_day()}

@router.post('/estimate')
def estimate(b:EstimateInput,u=Depends(current)):
    result=road_model.estimate(b.load_liters,b.wet_road,road_service.supervisor_value(u,b.supervisor_minutes))
    return {'minutes':result['minutes'],'source':result['source'],'requires_supervisor':result['requires_supervisor'],
        'basis':result['basis'],'evidence':result['evidence']}

@router.post('/closures')
def closure(b:ClosureInput,u=Depends(admin),db=Depends(session)):
    if u.role!='admin':raise HTTPException(403,'仅主管可以确认封路')
    row,lane,paused=road_service.confirm_closure(db,b,u)
    db.commit();return payload(lane,row,paused)

@router.post('/closures/{key}/lift')
def lift(key:int,b:RoadActionInput|None=None,u=Depends(admin),db=Depends(session)):
    row,lane=road_service.lift_closure(db,key,u)
    db.commit();return {'closure':row,'lane':lane}

@router.post('/reservations/{key}/enter')
def enter(key:int,b:RoadActionInput|None=None,u=Depends(editor),db=Depends(session)):
    row=road_service.enter(db,key,b or RoadActionInput(),u);db.commit();return row

@router.post('/reservations/{key}/exit')
def exit_reservation(key:int,b:RoadActionInput|None=None,u=Depends(editor),db=Depends(session)):
    row=road_service.exit_lane(db,key,b or RoadActionInput(),u);db.commit();return row

@router.post('/reservations/{key}/reschedule')
def reschedule(key:int,b:RescheduleInput,u=Depends(editor),db=Depends(session)):
    row=road_service.reschedule(db,key,b,u);db.commit();return row
