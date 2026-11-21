from datetime import date
from pydantic import Field
from .revisit_schemas import Inputs
class EstimateInput(Inputs):
    load_liters:float=Field(gt=0,le=100000)
    wet_road:bool=False
    supervisor_minutes:int|None=Field(default=None,ge=1,le=1440)
class ClosureInput(Inputs):
    work_date:date
    road_start:str=Field(min_length=4,max_length=5)
    minutes:int=Field(ge=1,le=1440)
    reason:str=Field(min_length=5,max_length=400)
    request_key:str|None=Field(default=None,min_length=8,max_length=80)
class RoadActionInput(Inputs):
    request_key:str|None=Field(default=None,min_length=8,max_length=80)
class RescheduleInput(Inputs):
    work_date:date
    road_start:str=Field(min_length=4,max_length=5)
    wet_road:bool|None=None
    load_liters:float|None=Field(default=None,gt=0,le=100000)
    supervisor_minutes:int|None=Field(default=None,ge=1,le=1440)
    request_key:str|None=Field(default=None,min_length=8,max_length=80)
