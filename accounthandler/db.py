from os import environ
from pymongo import MongoClient
from typing import List, Dict
from datetime import datetime
from pydantic import BaseModel

environ["MONGODB_URL"] = "192.168.178.36:30001"

DATABASE_URL = "mongodb://" + environ["MONGODB_URL"] # user:password@postgresserver/db

mongoclient = MongoClient(DATABASE_URL)
tradingDB = mongoclient["trading"]
accountsDB = tradingDB.accountsDB
tradesDB = tradingDB.tradesDB
errorsDB = tradingDB.errorsDB
pricehistoryDB = tradingDB.pricehistoryDB
socialRankDB = tradingDB.socialRankDB

class Account(BaseModel):
    name: str
    portfolio: Dict[str, float]
    lastTrade: datetime = datetime.utcnow()

class Trade(BaseModel):
    name: str
    amount: float
    price: float
    buy: bool
    timestamp: datetime = datetime.utcnow()

class Error(BaseModel):
    message: str
    timestamp: datetime = datetime.utcnow()

class PriceHistory(BaseModel):
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: datetime = datetime.utcnow()