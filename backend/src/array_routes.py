from fastapi import APIRouter,Depends
from sqlalchemy import select
from .database import session
from .auth import current,admin
from .models import ArrayBlock
from .schemas import ArrayInput
from .field_service import save_block
router=APIRouter(prefix='/arrays')
@router.get('')
def list_blocks(user=Depends(current),db=Depends(session)):return db.scalars(select(ArrayBlock).order_by(ArrayBlock.id)).all()
@router.post('')
def create(body:ArrayInput,user=Depends(admin),db=Depends(session)):return save_block(db,body,user)
@router.put('/{key}')
def change(key:int,body:ArrayInput,user=Depends(admin),db=Depends(session)):return save_block(db,body,user,key)
