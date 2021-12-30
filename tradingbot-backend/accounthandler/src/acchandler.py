from tinydb import TinyDB, Query
from fastapi import FastAPI, HTTPException, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi_login import LoginManager
from fastapi_login.exceptions import InvalidCredentialsException
from werkzeug.security import generate_password_hash
from pydantic import BaseModel
from typing import Optional, List
from os import environ
from dotenv import load_dotenv
from datetime import datetime, timedelta
from binance import Client
from binance.exceptions import BinanceAPIException
from json import loads
import uvicorn

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
    hashedPw: str
    description: Optional[str] = "A default bot"
    portfolio: List[PortfolioItem] = [PortfolioItem(symbol = "USDT", amount = 10000)]
    demo: Optional[bool] = True
    disabled: Optional[bool] = False

DEFAULTACCOUNTVALUE = 10000 # 10 000 usd

# SECURITY STUFF
manager = LoginManager(environ["SECRET"], token_url='/auth/token')
@manager.user_loader()
def load_user(name: str):  # could also be an asynchronous function
    res = db.search(Queryobject.name == name)
    if len(res) == 0:
        return None
    else:
        return Account(**res[0])

## login related stuff
@app.post('/auth/token')
def login(data: OAuth2PasswordRequestForm = Depends()):
    name = data.username
    password = data.password
    user = load_user(name)
    
    if not user:
        raise InvalidCredentialsException  # you can also use your own HTTPException
    elif __passwdHash(password) != user.hashedPw:
        raise InvalidCredentialsException
    
    access_token = manager.create_access_token(
        data=dict(sub=name)
    )
    return {'access_token': access_token, 'token_type': 'bearer'}

@app.get('/protected')
def protected_route(t = Depends(manager)):
    return {"message": "you are logged in!"}
## end login related stuff

def __passwdHash(passwd):
    return generate_password_hash(passwd, method='pbkdf2:sha512')

@app.post("/createNewAccount", response_model=Account)
async def createNewAccount(account: Account):
    # check if exists already
    res = db.search(Queryobject.name == account.name)
    if len(res) > 0:
        raise HTTPException(status_code=400, detail="Account already exists")
    else:
        account.hashedPw = __passwdHash(account.hashedPw)
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
    # return db.all()
    resp = []
    for acc in db.all():
        acc["hashedPw"] = "****"
        resp.append(acc)
    return resp
    
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


if __name__ == "__main__":
    uvicorn.run("acchandler:app", host="127.0.0.1", log_level="debug")