from fastapi import HTTPException
from sqlalchemy import select
from .models import ArrayBlock,SoilingSurvey,WashMission
from .revisit_models import FollowupSurvey
from .field_service import require,audit

def survey(db,body,user):
    mission=require(db,WashMission,body.mission_id,True)
    if mission.status!='accepted' or not mission.post_kw or not mission.post_irradiance:raise HTTPException(409,'只能复访已验收且保留复测功率的任务')
    original=require(db,SoilingSurvey,mission.survey_id)
    block=require(db,ArrayBlock,original.block_id,True)
    if block.cleaning_state=='washing':raise HTTPException(409,'阵列正在再次清洗，请在本次验收后复访')
    if body.observed_kw>original.capacity_kw*1.2:raise HTTPException(409,'复访功率超过额定容量120%')
    previous=db.scalar(select(FollowupSurvey).where(FollowupSurvey.mission_id==mission.id,FollowupSurvey.days_after>=body.days_after))
    if previous:raise HTTPException(409,'同任务复访天数必须递增，不可重复或倒序')
    normalized=body.observed_kw*mission.post_irradiance/body.irradiance
    loss=100*(mission.post_kw-normalized)/mission.post_kw
    item=FollowupSurvey(**body.model_dump(),normalized_kw=normalized,normalized_loss=loss,state='reinspect' if loss>5 else 'stable',baseline_snapshot={'post_kw':mission.post_kw,'post_irradiance':mission.post_irradiance,'accepted_at':mission.accepted_at.isoformat() if mission.accepted_at else None,'block_id':block.id,'block_code':block.code,'survey_id':original.id,'survey_code':original.code,'threshold_pct':5})
    db.add(item);audit(db,user,f'清洗复访 任务{mission.id} 第{body.days_after}天 归一化损失{loss:.2f}%');db.commit();return item

def close(db,key,body,user):
    item=require(db,FollowupSurvey,key,True)
    if item.state=='closed':raise HTTPException(409,'已关闭复访不可重复处置')
    mission=require(db,WashMission,item.mission_id)
    if item.state=='reinspect' and not body.new_survey_id:raise HTTPException(409,'损失超过5%，须登记新的同阵列巡测作为重巡依据')
    if body.new_survey_id:
        fresh=require(db,SoilingSurvey,body.new_survey_id)
        if fresh.id==mission.survey_id or fresh.block_id!=item.baseline_snapshot['block_id'] or fresh.state in ['closed','stale','scheduled','retested'] or (mission.accepted_at and fresh.taken_at<mission.accepted_at.replace(microsecond=0)):raise HTTPException(409,'须引用验收后新建的同阵列有效巡测，旧巡测不得重新派工')
    item.resolution=body.resolution;item.new_survey_id=body.new_survey_id;item.closed_by=user.email;item.state='closed'
    audit(db,user,f'关闭清洗复访 {key} 依据{body.resolution} 新巡测{body.new_survey_id or "无需"}');db.commit();return item
