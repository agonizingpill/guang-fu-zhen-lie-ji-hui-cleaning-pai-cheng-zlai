import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker,DeclarativeBase
engine=create_engine(os.getenv('DATABASE_URL','mysql+pymysql://solar:solar@db:3306/solar'),pool_pre_ping=True,isolation_level="READ COMMITTED")
Session=sessionmaker(engine,expire_on_commit=False)
class Base(DeclarativeBase):pass
def session():
    with Session() as db:yield db
