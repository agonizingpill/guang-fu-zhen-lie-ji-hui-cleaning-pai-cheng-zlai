import os,time,logging
from contextlib import asynccontextmanager
import redis
from sqlalchemy import select,text
from sqlalchemy.exc import IntegrityError
from fastapi import FastAPI,Depends,HTTPException,Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .database import Base,engine,session
from .models import User,Audit
from .schemas import Login
from .auth import current,hash_password,issue
from .array_routes import router as arrays
from .survey_routes import router as surveys
from .mission_routes import router as missions
from .revisit_routes import router as revisits
from .operations_routes import router as operations
queue=redis.Redis.from_url(os.getenv('REDIS_URL','redis://redis:6379/0'),decode_responses=True)
@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    if os.getenv('SEED_DEMO','true').lower()=='true':
        try:
            from scripts.seed_demo import seed
            seed()
        except Exception:logging.exception('seed failed')
    yield
app=FastAPI(title='晴岭 · 光伏积灰清洗排程',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:18223'],allow_methods=['*'],allow_headers=['*'])
@app.middleware('http')
async def trace(request:Request,call_next):
    start=time.monotonic();response=await call_next(request);response.headers['X-Elapsed-Ms']=str(round((time.monotonic()-start)*1000,2));return response
@app.middleware('http')
async def recover(request:Request,call_next):
    try:return await call_next(request)
    except IntegrityError:return JSONResponse({'detail':'编号或关联记录冲突，请刷新后重试'},409)
    except Exception:
        logging.exception('request failed');return JSONResponse({'detail':'现场记录暂时无法保存，请重试'},500)
@app.get('/health')
def health(db=Depends(session)):db.execute(text('SELECT 1'));queue.ping();return {'status':'ok'}
@app.post('/auth/login')
def login(body:Login,db=Depends(session)):
    user=db.scalar(select(User).where(User.email==body.email))
    if not user or user.password!=hash_password(body.password):raise HTTPException(401,'邮箱或密码错误')
    return {'token':issue(user),'email':user.email,'role':user.role}
@app.get('/audits')
def audits(user=Depends(current),db=Depends(session)):return db.scalars(select(Audit).order_by(Audit.id.desc()).limit(50)).all()
app.include_router(arrays);app.include_router(surveys);app.include_router(missions);app.include_router(revisits);app.include_router(operations)
