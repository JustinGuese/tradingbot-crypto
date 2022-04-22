from os import environ
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.types import DateTime
from sqlalchemy.orm import sessionmaker

# environ["PSQL_URL"] = "postgres:tradingbot@198.74.104.172:30001"

DATABASE_URL = "postgresql+psycopg2://" + environ["PSQL_URL"] # user:password@postgresserver/db

engine = create_engine(DATABASE_URL)
session = sessionmaker(bind=engine)()

Base = declarative_base()

class CryptoQualitySignal(Base):
    __tablename__ = "signals_cryptoqualitysignals"
    id = Column(Integer, primary_key=True, index=True, unique = True)
    timestamp = Column(DateTime)
    exchange = Column(String)
    currency = Column(String)
    coin = Column(String)
    direction = Column(String)
    buy_start = Column(Float)
    buy_end = Column(Float)
    target1 = Column(Float)
    target2 = Column(Float)
    target3 = Column(Float)
    stop_loss = Column(Float)
    type = Column(String)
    ask = Column(Float)
    risk_level = Column(Integer)
    created_at = Column(DateTime)
    executed = Column(Boolean, default = False)
    inExecution = Column(Boolean, default = False)

Base.metadata.create_all(engine)