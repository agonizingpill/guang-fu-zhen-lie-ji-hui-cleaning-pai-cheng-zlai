from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import select
from .models import ArrayBlock
from .revisit_models import WaterDelivery
from .field_service import require,audit

def plan(db,body,user):
    require(db,ArrayBlock,body.block_id)
    if db.scalar(select(WaterDelivery).where(WaterDelivery.delivery_code==body.delivery_code)):raise HTTPException(409,'补给编号已存在')
    item=WaterDelivery(**body.model_dump());db.add(item)
    audit(db,user,f'计划补水 {body.delivery_code} {body.liters}L 来源{body.source}');db.commit();return item

def receive(db,key,body,user):
    item=require(db,WaterDelivery,key,True)
    if item.state!='planned':raise HTTPException(409,'仅待到货计划可确认，实收凭据不可重复覆盖')
    if body.received_liters>item.liters:raise HTTPException(409,'实收水量不得超过计划水量')
    item.received_liters=body.received_liters;item.received_by=user.email;item.state='received'
    audit(db,user,f'现场确认补水 {item.delivery_code} 实收{item.received_liters}L');db.commit();return item

def credit(db,key,user):
    item=require(db,WaterDelivery,key,True)
    if item.state!='received':raise HTTPException(409,'须先确认实收，且不能重复入额')
    block=require(db,ArrayBlock,item.block_id,True)
    if block.cleaning_state=='washing':raise HTTPException(409,'阵列清洗中，补给须等待验收后入额')
    if block.water_liters+item.received_liters>100000:raise HTTPException(409,'入额后超过阵列100000L配额上限')
    block.water_liters=round(block.water_liters+item.received_liters,3)
    item.state='credited';item.credited_by=user.email;item.credited_at=datetime.utcnow()
    audit(db,user,f'补水入额 {item.delivery_code} +{item.received_liters}L 余{block.water_liters}L');db.commit();return item
