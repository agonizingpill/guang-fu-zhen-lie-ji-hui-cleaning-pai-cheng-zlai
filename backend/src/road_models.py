from datetime import date,datetime
from sqlalchemy import String,Float,ForeignKey,JSON,CheckConstraint,Date,DateTime,Boolean,func
from sqlalchemy.orm import Mapped,mapped_column
from .database import Base

LANE_CODE='NORTH-SLOPE'
LANE_NAME='北坡便道'

class RoadLane(Base):
    """Singleton row serializing every north-road state change.

    The lane row is locked FOR UPDATE before booking, entry, exit, closure and
    reschedule. MySQL READ COMMITTED then observes the preceding commit.
    """
    __tablename__='road_lanes'
    id:Mapped[int]=mapped_column(primary_key=True)
    code:Mapped[str]=mapped_column(String(40),unique=True)
    status:Mapped[str]=mapped_column(String(16),default='open')
    active_closure_id:Mapped[int|None]=mapped_column(nullable=True)

class RoadReservation(Base):
    __tablename__='road_reservations'
    __table_args__=(CheckConstraint('start_minute>=0 AND start_minute<=1439 AND (minutes IS NULL OR minutes>0)'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    permit_id:Mapped[int]=mapped_column(ForeignKey('work_permits.id'),unique=True)
    road_code:Mapped[str]=mapped_column(String(40),default=LANE_CODE)
    work_date:Mapped[date]=mapped_column(Date)
    start_minute:Mapped[int]=mapped_column()
    minutes:Mapped[int|None]=mapped_column(nullable=True)
    wet_road:Mapped[bool]=mapped_column(Boolean,default=False)
    load_liters:Mapped[float]=mapped_column(Float)
    state:Mapped[str]=mapped_column(String(20),default='draft')
    estimate_source:Mapped[str]=mapped_column(String(20),default='model')
    estimate_basis:Mapped[str]=mapped_column(String(500),default='')
    estimate_evidence:Mapped[dict|None]=mapped_column(JSON,nullable=True)
    paused_by_closure_id:Mapped[int|None]=mapped_column(ForeignKey('road_closures.id'),nullable=True)
    reschedule_count:Mapped[int]=mapped_column(default=0)
    entered_at:Mapped[datetime|None]=mapped_column(DateTime,nullable=True)
    exited_at:Mapped[datetime|None]=mapped_column(DateTime,nullable=True)
    overtime_minutes:Mapped[int]=mapped_column(default=0)
    created_at:Mapped[datetime]=mapped_column(DateTime,server_default=func.now())

class RoadClosure(Base):
    __tablename__='road_closures'
    __table_args__=(CheckConstraint('start_minute>=0 AND start_minute<=1439 AND minutes>0'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    road_code:Mapped[str]=mapped_column(String(40),default=LANE_CODE)
    work_date:Mapped[date]=mapped_column(Date)
    start_minute:Mapped[int]=mapped_column()
    minutes:Mapped[int]=mapped_column()
    reason:Mapped[str]=mapped_column(String(400))
    state:Mapped[str]=mapped_column(String(16),default='confirmed')
    confirmed_by:Mapped[str]=mapped_column(String(120),default='')
    lifted_by:Mapped[str]=mapped_column(String(120),default='')
    confirmed_at:Mapped[datetime]=mapped_column(DateTime,server_default=func.now())
    lifted_at:Mapped[datetime|None]=mapped_column(DateTime,nullable=True)

class RoadRequest(Base):
    """Idempotency ledger for road mutations keyed by client request_key.

    The lane lock serializes the key lookup and the mutation, so a disconnected
    retry replays the first result instead of booking a second slot.
    """
    __tablename__='road_requests'
    id:Mapped[int]=mapped_column(primary_key=True)
    request_key:Mapped[str]=mapped_column(String(80),unique=True)
    action:Mapped[str]=mapped_column(String(40))
    result_type:Mapped[str]=mapped_column(String(20))
    result_id:Mapped[int]=mapped_column()
    actor:Mapped[str]=mapped_column(String(120),default='')
    created_at:Mapped[datetime]=mapped_column(DateTime,server_default=func.now())
