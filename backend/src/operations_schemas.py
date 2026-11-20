from datetime import date
from pydantic import Field,field_validator
from .revisit_schemas import Inputs
class CrewInput(Inputs):
    code:str=Field(min_length=2,max_length=40)
    max_daily_minutes:int=Field(ge=1,le=1440)
class CrewState(Inputs):
    active:bool
class PermitInput(Inputs):
    mission_id:int
    crew_id:int
    work_date:date
    minutes:int=Field(ge=1,le=1440)
    wind_mps:float=Field(ge=0,le=60)
    isolation:bool
class WasteInput(Inputs):
    mission_id:int
    recovered_liters:float=Field(ge=0,le=100000)
    disposal_method:str=Field(min_length=3,max_length=160)
    low_recovery_reason:str=Field(default='',max_length=400)
    manifest:str=Field(min_length=2,max_length=80)
class HandoverInput(Inputs):
    received_by:str=Field(min_length=2,max_length=120)
    receipt:str=Field(min_length=5,max_length=200)
class SettlementInput(Inputs):
    mission_id:int
    price_per_kw:float=Field(gt=0,le=100000)
    cost_per_liter:float=Field(ge=0,le=10000)
    negative_reason:str=Field(default='',max_length=400)
