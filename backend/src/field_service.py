from fastapi import HTTPException
from sqlalchemy import select
from .models import ArrayBlock,SoilingSurvey,WashMission,Audit

def require(db,model,key,lock=False):
    query=select(model).where(model.id==key)
    if lock:query=query.with_for_update().execution_options(populate_existing=True)
    item=db.scalar(query)
    if not item:raise HTTPException(404,'现场记录不存在')
    return item

def audit(db,user,message):db.add(Audit(actor=user.email,action=message))

def save_block(db,body,user,key=None):
    if key:
        block=require(db,ArrayBlock,key,True)
        if block.cleaning_state=='washing':raise HTTPException(409,'阵列正在清洗，不可调整规格或水量配额')
        if abs(block.water_liters-body.water_liters)>0.0001:raise HTTPException(409,'既有阵列水量须通过补水入额变更，不能直接覆盖')
        existing=db.scalar(select(ArrayBlock).where(ArrayBlock.code==body.code,ArrayBlock.id!=key))
    else:block=ArrayBlock();existing=db.scalar(select(ArrayBlock).where(ArrayBlock.code==body.code))
    if existing:raise HTTPException(409,'阵列编号已存在')
    for k,v in body.model_dump().items():setattr(block,k,v)
    db.add(block);audit(db,user,f'维护阵列 {body.code}，可用水量{body.water_liters}L');db.commit();return block

def record_survey(db,body,user):
    block=require(db,ArrayBlock,body.block_id)
    if block.cleaning_state=='washing':raise HTTPException(409,'清洗执行中，请在复测页登记清洗后读数')
    if body.observed_kw>block.capacity_kw*1.2:raise HTTPException(409,'观测功率超过阵列额定容量120%，请核对电表口径')
    if db.scalar(select(SoilingSurvey).where(SoilingSurvey.code==body.code)):raise HTTPException(409,'巡测编号已存在')
    survey=SoilingSurvey(**body.model_dump(),capacity_kw=block.capacity_kw,slope=block.slope)
    db.add(survey);audit(db,user,f'巡测 {body.code}，{body.irradiance}W/m² / {body.observed_kw}kW');db.commit();return survey

def queue_assessment(db,key,user,queue):
    survey=require(db,SoilingSurvey,key,True)
    if survey.irradiance<350:raise HTTPException(409,'辐照低于350 W/m²，禁止估损，请重新巡测')
    if not (80<=survey.capacity_kw<=150 and 350<=survey.irradiance<=1050 and 18<=survey.module_temp<=65 and 10<=survey.slope<=35):raise HTTPException(409,'巡测超出本站标定范围，请人工复核后重新采样')
    if survey.state not in ['recorded','blocked']:raise HTTPException(409,'巡测已评估或已排程，请勿重复提交')
    block=require(db,ArrayBlock,survey.block_id,True)
    if block.cleaning_state=='washing':raise HTTPException(409,'该阵列清洗执行中，旧巡测不能再评估')
    survey.state='evaluating';audit(db,user,f'评估积灰 {survey.code}');db.commit();queue.rpush('solar:assessment',str(survey.id));return survey
