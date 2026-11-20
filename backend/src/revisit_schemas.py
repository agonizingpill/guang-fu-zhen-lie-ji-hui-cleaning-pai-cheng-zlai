from pydantic import BaseModel,Field,ConfigDict,field_validator
class Inputs(BaseModel):
    model_config=ConfigDict(allow_inf_nan=False)
class DeliveryInput(Inputs):
    block_id:int
    delivery_code:str=Field(min_length=1,max_length=50)
    liters:float=Field(gt=0,le=100000)
    source:str=Field(min_length=3,max_length=120)
    @field_validator('delivery_code','source')
    @classmethod
    def nonempty(cls,v):
        if not v.strip():raise ValueError('不能为空')
        return v.strip()
class ReceiveInput(Inputs):
    received_liters:float=Field(gt=0,le=100000)
class FollowupInput(Inputs):
    mission_id:int
    days_after:int=Field(ge=1,le=365)
    irradiance:float=Field(ge=350,le=1400)
    observed_kw:float=Field(ge=0,le=10000)
class CloseInput(Inputs):
    resolution:str=Field(min_length=5,max_length=500)
    new_survey_id:int|None=None
    @field_validator('resolution')
    @classmethod
    def reason(cls,v):
        if len(v.strip())<5:raise ValueError('处置依据至少5字')
        return v.strip()
