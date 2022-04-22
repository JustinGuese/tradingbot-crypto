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

# environ["PSQL_URL"] = "postgres:tradingbot@198.74.104.172:30001"

DATABASE_URL = "postgresql+psycopg2://" + environ["PSQL_URL"] # user:password@postgresserver/db

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# declarative base
class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(30), unique=True)
    description = Column(String(100))
    portfolio = Column(MutableDict.as_mutable(JSON))
    lastTrade = Column(DateTime)
    netWorth = Column(Float)
    lastUpdateWorth = Column(DateTime)
    createdAt = Column(DateTime, default = datetime.utcnow)

class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True, index=True)
    accountname = Column(String(30))
    symbol = Column(String(10))
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

class FearGreedIndex(Base):
    __tablename__ = "marketinfo_feargreedindex"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime)
    # "now", "yesterday", "1weekago", "1monthago", "1yearago"
    now = Column(Integer)
    yesterday = Column(Integer)
    weekago = Column(Integer)
    monthago = Column(Integer)
    yearago = Column(Integer)

class BinanceRecentTrade(Base):
    __tablename__ = "binance_recentTrades"
    id = Column(Integer, primary_key=True)
    time = Column(DateTime)
    symbol = Column(String)
    price = Column(Float)
    qty = Column(Float)
    quoteQty = Column(Float)
    isBuyerMaker = Column(Boolean)
    isBestMatch = Column(Boolean)

class StockData(Base):
    __tablename__ = "stock_data"
    id = Column(Integer, primary_key=True)
    date = Column(DateTime)
    symbol = Column(String(10))
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)

class TASummary(Base):
    __tablename__ = "stock_ta_summary"
    id = Column(Integer, primary_key=True)
    symbol = Column(String)
    timestamp = Column(DateTime)
    recommendation = Column(String)
    buyCnt = Column(Integer)
    neutralCnt = Column(Integer)
    sellCnt = Column(Integer)
# pydantic models

    # id = Column(Integer, primary_key=True, index=True)
    # name = Column(String(30), unique=True)
    # description = Column(String(100))
    # portfolio = Column(MutableDict.as_mutable(JSON))
    # lastTrade = Column(DateTime)
    # netWorth = Column(Float)
    # lastUpdateWorth = Column(DateTime)
    # createdAt = Column(DateTime, default = datetime.utcnow)
class AccountPD(BaseModel):
    id: int
    name: str
    description: str
    portfolio: Dict[str, float]
    lastTrade: datetime = datetime.utcnow()
    netWorth: float = 10000.0
    lastUpdateWorth: datetime = datetime.utcnow()
    createdAt: datetime = datetime.utcnow()
    class Config:
        orm_mode = True

class TradePD(BaseModel):
    id: int
    accountname: str
    symbol: str
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