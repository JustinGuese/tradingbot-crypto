from tinydb import TinyDB, Query
from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from typing import Optional
from os import environ
from dotenv import load_dotenv
from datetime import datetime, timedelta
from binance import Client

load_dotenv()  # take environment variables from .env.

client = Client(environ["BINANCE_KEY"], environ["BINANCE_SECRET"])

db = TinyDB('persistent/currentAccounts.json')
lastPrices = TinyDB('persistent/lastPrices.json')
app = FastAPI()
Queryobject = Query()

PRICEQUERYCACHE = 1 # minutes

#fastapi models
class Portfolio(BaseModel):
    symbol: str = "USDT"
    amount: Optional[float] = 10000
class Account(BaseModel):
    name: str
    description: Optional[str] = "A default bot"
    portfolio: Portfolio
    

DEFAULTACCOUNTVALUE = 10000 # 10 000 usd

@app.post("/accounts")
async def createNewAccount(account: Account):
    # check if exists already
    res = db.search(Queryobject.name == account.name)
    if len(res) > 0:
        raise HTTPException(status_code=400, detail="Account already exists")
    else:
        db.insert(jsonable_encoder(account))
        return account
    
def __getStringNow():
    return __codeTimestamp(datetime.utcnow())
    
def __codeTimestamp(stringTS):
    return datetime.strftime(stringTS, "%Y-%m-%dT%H:%M:%S")

def __decodeTimestamp(timestamp):
    return datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S")
    
def __getBinancePrice(symbol):
    return float(client.get_avg_price(symbol=symbol)["price"])

def __getCurrentPrice(symbol):
    # symbol has to be like BTCUSDT
    # try to save querying the api with lookup
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
    
@app.get("/currentPrice")
async def getCurrentPrice(symbol: str):
    return __getCurrentPrice(symbol)