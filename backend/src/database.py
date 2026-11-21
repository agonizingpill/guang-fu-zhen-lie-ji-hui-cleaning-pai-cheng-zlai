import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker,DeclarativeBase
URL=os.getenv('DATABASE_URL','mysql+pymysql://solar:solar@db:3306/solar')
# READ COMMITTED lets a lane/crew row lock observe the preceding signer's commit.
# SQLite only offers the three built-in modes, so local scratch databases skip it.
OPTIONS={} if URL.startswith('sqlite') else {'isolation_level':'READ COMMITTED'}
engine=create_engine(URL,pool_pre_ping=True,**OPTIONS)
Session=sessionmaker(engine,expire_on_commit=False)
class Base(DeclarativeBase):pass
def session():
    with Session() as db:yield db
