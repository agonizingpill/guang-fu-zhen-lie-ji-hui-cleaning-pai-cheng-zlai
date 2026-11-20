from pydantic import BaseModel,Field
class Login(BaseModel):
    email:str
    password:str
class ArrayInput(BaseModel):
    code:str=Field(min_length=1,max_length=40)
    name:str=Field(min_length=1,max_length=80)
    sector:str=Field(min_length=1,max_length=30)
    capacity_kw:float=Field(gt=0,le=10000)
    slope:float=Field(ge=0,le=60)
    area_m2:float=Field(gt=0,le=100000)
    water_liters:float=Field(ge=0,le=100000)
class SurveyInput(BaseModel):
    code:str=Field(min_length=1,max_length=50)
    block_id:int
    irradiance:float=Field(gt=0,le=1400)
    module_temp:float=Field(ge=-20,le=85)
    rain_days:int=Field(ge=0,le=180)
    dust:float=Field(ge=0,le=10)
    observed_kw:float=Field(ge=0,le=10000)
class MissionInput(BaseModel):
    survey_id:int
    water_liters:float=Field(gt=0,le=100000)
class WaterRevision(BaseModel):
    water_liters:float=Field(gt=0,le=100000)
class RetestInput(BaseModel):
    post_kw:float=Field(gt=0,le=10000)
    post_irradiance:float=Field(ge=350,le=1400)
