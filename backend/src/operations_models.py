from datetime import date,datetime
from sqlalchemy import String,Float,ForeignKey,JSON,CheckConstraint,Date,DateTime,func
from sqlalchemy.orm import Mapped,mapped_column
from .database import Base
class WashCrew(Base):
    __tablename__='wash_crews'
    __table_args__=(CheckConstraint('max_daily_minutes>0'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    code:Mapped[str]=mapped_column(String(40),unique=True)
    max_daily_minutes:Mapped[int]=mapped_column()
    active:Mapped[bool]=mapped_column(default=True)
class WorkPermit(Base):
    __tablename__='work_permits'
    __table_args__=(CheckConstraint('minutes>0 AND wind_mps>=0'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    mission_id:Mapped[int]=mapped_column(ForeignKey('wash_missions.id'),unique=True)
    crew_id:Mapped[int]=mapped_column(ForeignKey('wash_crews.id'))
    work_date:Mapped[date]=mapped_column(Date)
    minutes:Mapped[int]=mapped_column()
    wind_mps:Mapped[float]=mapped_column(Float)
    isolation:Mapped[bool]=mapped_column()
    state:Mapped[str]=mapped_column(String(24),default='draft')
    signed_by:Mapped[str]=mapped_column(String(120),default='')
class WastewaterRecord(Base):
    __tablename__='wastewater_records'
    __table_args__=(CheckConstraint('recovered_liters>=0 AND recovered_liters<=used_liters AND used_liters>0'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    mission_id:Mapped[int]=mapped_column(ForeignKey('wash_missions.id'),unique=True)
    used_liters:Mapped[float]=mapped_column(Float)
    recovered_liters:Mapped[float]=mapped_column(Float)
    recovery_pct:Mapped[float]=mapped_column(Float)
    disposal_method:Mapped[str]=mapped_column(String(160))
    low_recovery_reason:Mapped[str]=mapped_column(String(400),default='')
    manifest:Mapped[str]=mapped_column(String(80),unique=True)
    state:Mapped[str]=mapped_column(String(24),default='recorded')
    verified_by:Mapped[str]=mapped_column(String(120),default='')
    received_by:Mapped[str]=mapped_column(String(120),default='')
    receipt:Mapped[str]=mapped_column(String(200),default='')
class WashSettlement(Base):
    __tablename__='wash_settlements'
    __table_args__=(CheckConstraint('price_per_kw>0 AND cost_per_liter>=0'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    mission_id:Mapped[int]=mapped_column(ForeignKey('wash_missions.id'),unique=True)
    price_per_kw:Mapped[float]=mapped_column(Float)
    cost_per_liter:Mapped[float]=mapped_column(Float)
    revenue:Mapped[float]=mapped_column(Float)
    water_cost:Mapped[float]=mapped_column(Float)
    margin:Mapped[float]=mapped_column(Float)
    negative_reason:Mapped[str]=mapped_column(String(400),default='')
    snapshot:Mapped[dict]=mapped_column(JSON)
    state:Mapped[str]=mapped_column(String(24),default='draft')
    signed_by:Mapped[str]=mapped_column(String(120),default='')
    signed_at:Mapped[datetime|None]=mapped_column(DateTime,nullable=True)
