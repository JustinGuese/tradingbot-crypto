from tinydb import TinyDB, Query
from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from typing import Optional, List
from os import environ
from dotenv import load_dotenv
from datetime import datetime, timedelta
from binance import Client
from binance.exceptions import BinanceAPIException
from json import loads

load_dotenv()  # take environment variables from .env.

client = Client(environ["BINANCE_KEY"], environ["BINANCE_SECRET"])

db = TinyDB('persistent/currentAccounts.json')
lastPrices = TinyDB('persistent/lastPrices.json')
app = FastAPI()
Queryobject = Query()

PRICEQUERYCACHE = 3 # minutes

#fastapi models
class PortfolioItem(BaseModel):
    symbol: str = "USDT"
    amount: Optional[float] = 10000
class Account(BaseModel):
    name: str
    description: Optional[str] = "A default bot"
    portfolio: List[PortfolioItem] = [PortfolioItem(symbol = "USDT", amount = 10000)]
    

DEFAULTACCOUNTVALUE = 10000 # 10 000 usd

@app.post("/accounts", response_model=Account)
async def createNewAccount(account: Account):
    # check if exists already
    res = db.search(Queryobject.name == account.name)
    if len(res) > 0:
        raise HTTPException(status_code=400, detail="Account already exists")
    else:
        db.insert(jsonable_encoder(account))
        return account
    
@app.get("/getPortfolio", response_model = List[PortfolioItem])
async def getPortfolio(accountName: str):
    res = db.search(Queryobject.name == accountName)
    if len(res) == 0:
        raise HTTPException(status_code=404, detail="Account does not exists")
    else:
        return res[0]["portfolio"]
    
@app.get("/getPortfolioWorth", response_model = float)
async def getPortfolioWorth(accountName: str):
    res = db.search(Queryobject.name == accountName)
    if len(res) == 0:
        raise HTTPException(status_code=404, detail="Account does not exists")
    else:
        portfolio = res[0]["portfolio"]
        total = 0.
        for item in portfolio:
            total += float(item["amount"]) * __getCurrentPrice(item["symbol"])
        return total
    
@app.get("/getAllAccounts", response_model = List[Account])
async def getAllAccounts():
    return db.all()
    
def __getStringNow():
    return __codeTimestamp(datetime.utcnow())
    
def __codeTimestamp(stringTS):
    return datetime.strftime(stringTS, "%Y-%m-%dT%H:%M:%S")

def __decodeTimestamp(timestamp):
    return datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S")
    
def __getBinancePrice(symbol):
    try:
        price = float(client.get_avg_price(symbol=symbol)["price"])
    except BinanceAPIException as e:
        print("BinanceAPIException for symbol: " + str(symbol))
        raise e
    return 

def __getCurrentPrice(symbol):
    # symbol has to be like BTCUSDT
    # try to save querying the api with lookup
    # handle non direct lookups
    if "USDT" not in symbol:
        symbol += "USDT"
    elif symbol == "USDT":
        # simplest case
        return 1.
    
    res = db.search(Queryobject.symbol == symbol)
    price = 0.
    if len(res) > 0:
        # if it is there check the timestamp
        if __decodeTimestamp(res[0]["timestamp"]) + timedelta(minutes=PRICEQUERYCACHE) > datetime.utcnow():
            price = float(res[0]["price"])
        else: # we have to update current price
            price = __getBinancePrice(symbol)
            upd = {'price': price, 'timestamp': __getStringNow()}
            lastPrices.update(upd, Queryobject.symbol == symbol)
    else: # we have to create the entry
        price = __getBinancePrice(symbol)
        js = {'symbol': symbol, 'price': price, 'timestamp': __getStringNow()}
        lastPrices.insert(js)
    if price != 0.:
        # last check
        return price
    else:
        raise Exception("uhoh, price is 0. somehow, something went wrong!")
    
@app.get("/currentPrice", response_model = float)
async def getCurrentPrice(symbol: str):
    return __getCurrentPrice(symbol)