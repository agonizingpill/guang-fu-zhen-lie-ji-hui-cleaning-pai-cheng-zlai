import os,time,json,traceback
from pathlib import Path
from sqlalchemy import select
import redis
from .database import Session
from .models import ArrayBlock,SoilingSurvey
from .power_model import estimate
queue=redis.Redis.from_url(os.getenv('REDIS_URL','redis://redis:6379/0'),decode_responses=True)
while True:
    Path('/tmp/solar-heartbeat').touch()
    job=queue.blpop('solar:assessment',timeout=3)
    if not job:continue
    key=int(job[1])
    try:
        with Session() as db:
            survey=db.scalar(select(SoilingSurvey).where(SoilingSurvey.id==key).with_for_update())
            if not survey or survey.state!='evaluating':continue
            block=db.get(ArrayBlock,survey.block_id)
            clean,loss,evidence=estimate(survey)
            survey.clean_kw=clean;survey.predicted_loss=loss;survey.model_evidence=evidence
            survey.recommended_water=round(block.area_m2*.6*(1+.1*survey.dust),1)
            survey.state='assessed';db.commit()
            Path('/artifacts').mkdir(exist_ok=True)
            Path(f'/artifacts/survey-{key}.json').write_text(json.dumps({'survey_id':key,'clean_kw':clean,'loss_kw':loss,'model':evidence}))
    except Exception as error:
        traceback.print_exc()
        with Session() as db:
            survey=db.get(SoilingSurvey,key)
            if survey:survey.state='blocked';survey.model_evidence={'error':str(error)};db.commit()
