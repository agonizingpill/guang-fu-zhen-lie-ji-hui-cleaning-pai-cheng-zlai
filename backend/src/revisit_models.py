from datetime import datetime
from sqlalchemy import String, Float, ForeignKey, JSON, CheckConstraint, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

class WaterDelivery(Base):
    __tablename__='water_deliveries'
    __table_args__=(CheckConstraint('liters>0 AND received_liters>=0 AND received_liters<=liters'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    block_id:Mapped[int]=mapped_column(ForeignKey('array_blocks.id'))
    delivery_code:Mapped[str]=mapped_column(String(50),unique=True)
    liters:Mapped[float]=mapped_column(Float)
    source:Mapped[str]=mapped_column(String(120))
    received_liters:Mapped[float]=mapped_column(Float,default=0)
    state:Mapped[str]=mapped_column(String(24),default='planned')
    received_by:Mapped[str]=mapped_column(String(120),default='')
    credited_by:Mapped[str]=mapped_column(String(120),default='')
    credited_at:Mapped[datetime|None]=mapped_column(DateTime,nullable=True)

class FollowupSurvey(Base):
    __tablename__='followup_surveys'
    __table_args__=(CheckConstraint('days_after>0 AND irradiance>=350 AND observed_kw>=0'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    mission_id:Mapped[int]=mapped_column(ForeignKey('wash_missions.id'))
    days_after:Mapped[int]=mapped_column()
    irradiance:Mapped[float]=mapped_column(Float)
    observed_kw:Mapped[float]=mapped_column(Float)
    normalized_kw:Mapped[float]=mapped_column(Float)
    normalized_loss:Mapped[float]=mapped_column(Float)
    baseline_snapshot:Mapped[dict]=mapped_column(JSON)
    state:Mapped[str]=mapped_column(String(24))
    resolution:Mapped[str]=mapped_column(String(500),default='')
    new_survey_id:Mapped[int|None]=mapped_column(ForeignKey('soiling_surveys.id'),nullable=True)
    closed_by:Mapped[str]=mapped_column(String(120),default='')
    created_at:Mapped[datetime]=mapped_column(DateTime,server_default=func.now())
