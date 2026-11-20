from datetime import datetime
from sqlalchemy import String,Float,ForeignKey,JSON,CheckConstraint,DateTime,func
from sqlalchemy.orm import Mapped,mapped_column
from .database import Base
class User(Base):
    __tablename__='users'
    id:Mapped[int]=mapped_column(primary_key=True)
    email:Mapped[str]=mapped_column(String(120),unique=True)
    password:Mapped[str]=mapped_column(String(240))
    role:Mapped[str]=mapped_column(String(20))
class ArrayBlock(Base):
    __tablename__='array_blocks'
    __table_args__=(CheckConstraint('capacity_kw>0 AND area_m2>0 AND water_liters>=0 AND slope>=0 AND slope<=60'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    code:Mapped[str]=mapped_column(String(40),unique=True)
    name:Mapped[str]=mapped_column(String(80))
    sector:Mapped[str]=mapped_column(String(30))
    capacity_kw:Mapped[float]=mapped_column(Float)
    slope:Mapped[float]=mapped_column(Float)
    area_m2:Mapped[float]=mapped_column(Float)
    water_liters:Mapped[float]=mapped_column(Float)
    cleaning_state:Mapped[str]=mapped_column(String(24),default='ready')
    last_cleaned:Mapped[datetime|None]=mapped_column(DateTime,nullable=True)
class SoilingSurvey(Base):
    __tablename__='soiling_surveys'
    __table_args__=(CheckConstraint('irradiance>0 AND observed_kw>=0 AND rain_days>=0 AND dust>=0'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    code:Mapped[str]=mapped_column(String(50),unique=True)
    block_id:Mapped[int]=mapped_column(ForeignKey('array_blocks.id'))
    capacity_kw:Mapped[float]=mapped_column(Float)
    slope:Mapped[float]=mapped_column(Float)
    irradiance:Mapped[float]=mapped_column(Float)
    module_temp:Mapped[float]=mapped_column(Float)
    rain_days:Mapped[int]=mapped_column()
    dust:Mapped[float]=mapped_column(Float)
    observed_kw:Mapped[float]=mapped_column(Float)
    clean_kw:Mapped[float|None]=mapped_column(Float,nullable=True)
    predicted_loss:Mapped[float|None]=mapped_column(Float,nullable=True)
    recommended_water:Mapped[float|None]=mapped_column(Float,nullable=True)
    model_evidence:Mapped[dict|None]=mapped_column(JSON,nullable=True)
    state:Mapped[str]=mapped_column(String(24),default='recorded')
    taken_at:Mapped[datetime]=mapped_column(DateTime,server_default=func.now())
class WashMission(Base):
    __tablename__='wash_missions'
    __table_args__=(CheckConstraint('water_liters>0 AND available_liters>=0'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    survey_id:Mapped[int]=mapped_column(ForeignKey('soiling_surveys.id'),unique=True)
    water_liters:Mapped[float]=mapped_column(Float)
    available_liters:Mapped[float]=mapped_column(Float)
    status:Mapped[str]=mapped_column(String(24),default='draft')
    post_kw:Mapped[float|None]=mapped_column(Float,nullable=True)
    post_irradiance:Mapped[float|None]=mapped_column(Float,nullable=True)
    normalized_kw:Mapped[float|None]=mapped_column(Float,nullable=True)
    verified_gain:Mapped[float|None]=mapped_column(Float,nullable=True)
    dispatched_at:Mapped[datetime|None]=mapped_column(DateTime,nullable=True)
    accepted_at:Mapped[datetime|None]=mapped_column(DateTime,nullable=True)
class Audit(Base):
    __tablename__='audits'
    id:Mapped[int]=mapped_column(primary_key=True)
    actor:Mapped[str]=mapped_column(String(120))
    action:Mapped[str]=mapped_column(String(240))
    at:Mapped[datetime]=mapped_column(DateTime,server_default=func.now())
