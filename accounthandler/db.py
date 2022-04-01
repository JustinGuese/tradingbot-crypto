from os import environ
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, Boolean, JSON, Float
from sqlalchemy.types import DateTime
from typing import List, Dict
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy.ext.mutable import MutableDict
from dotenv import load_dotenv
load_dotenv() 

# environ["PSQL_URL"] = "postgres:tradingbot@192.168.178.36:30001"

DATABASE_URL = "postgresql+psycopg2://" + environ["PSQL_URL"] # user:password@postgresserver/db

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# declarative base
class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(10), unique=True)
    description = Column(String(100))
    portfolio = Column(MutableDict.as_mutable(JSON))
    lastTrade = Column(DateTime)
    netWorth = Column(Float)
    lastUpdateWorth = Column(DateTime)

class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True, index=True)
    name= Column(String(30))
    amount= Column(Float)
    price= Column(Float)
    buy= Column(Boolean)
    timestamp= Column(DateTime)

class Error(Base):
    __tablename__ = "errors"
    id = Column(Integer, primary_key=True, index=True)
    message= Column(String(30))
    timestamp= Column(DateTime)

class PriceHistory(Base):
    __tablename__ = "pricehistory"
    id = Column(String(30), primary_key=True, index=True)
    symbol= Column(String(30))
    open= Column(Float)
    high= Column(Float)
    low= Column(Float)
    close= Column(Float)
    volume= Column(Float)
    nrTrades = Column(Integer)
    tbbasevolume = Column(Float)
    tbquotevolume = Column(Float)
    opentime= Column(DateTime)

class ApeRank(Base):
    __tablename__ = "social_aperank"
    id = Column(Integer, primary_key=True, index=True)
    rank = Column(Integer)
    ticker = Column(String(10))
    timestamp = Column(DateTime)
    mentions = Column(Integer)
    upvotes = Column(Integer)

class CoinGeckoTrending(Base):
    __tablename__ = "coingecko_trending"
    id = Column(Integer, primary_key=True, index=True)
    rank = Column(Integer)
    ticker = Column(String(10))
    timestamp = Column(DateTime)
    marketcaprank = Column(Integer)

class PortfolioTracker(Base):
    __tablename__ = "portfoliotracker"
    id = Column(Integer, primary_key=True, index=True)
    accountname = Column(String())
    portfolioworth = Column(Float)
    timestamp = Column(DateTime)

# pydantic models

class AccountPD(BaseModel):
    id: int
    name: str
    portfolio: Dict[str, float]
    lastTrade: datetime = datetime.utcnow()
    class Config:
        orm_mode = True

class TradePD(BaseModel):
    id: int
    name: str
    amount: float
    price: float
    buy: bool
    timestamp: datetime = datetime.utcnow()
    class Config:
        orm_mode = True

class ErrorPD(BaseModel):
    id: int
    message: str
    timestamp: datetime = datetime.utcnow()
    class Config:
        orm_mode = True

class PriceHistoryPD(BaseModel):
    id: str
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    nrTrades: int
    tbbasevolume: float
    tbquotevolume: float
    opentime: datetime = datetime.utcnow()
    class Config:
        orm_mode = True