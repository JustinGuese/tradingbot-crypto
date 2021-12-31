from tinydb import TinyDB, Query
from fastapi import FastAPI, HTTPException, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi_login import LoginManager
from fastapi_login.exceptions import InvalidCredentialsException
from werkzeug.security import generate_password_hash, check_password_hash
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

COMMISSION = 0.000025 # pct binance

#fastapi models
class Account(BaseModel):
    name: str
    hashedPw: str
    description: Optional[str] = "A default bot"
    portfolio: Optional[dict] = {"USDT":  10000}
    demo: Optional[bool] = True
    disabled: Optional[bool] = False

DEFAULTACCOUNTVALUE = 10000 # 10 000 usd

# SECURITY STUFF
manager = LoginManager(environ["SECRET"], '/login') # , use_cookie=True
@manager.user_loader()

def load_user(name: str):  # could also be an asynchronous function
    res = db.search(Queryobject.name == name)
    if len(res) == 0:
        return None
    else:
        return Account(**res[0])

## login related stuff
@app.post('/login')
def login(data: OAuth2PasswordRequestForm = Depends()):
    name = data.username
    password = data.password
    user = load_user(name)
    
    if not user:
        print("user not found")
        raise InvalidCredentialsException  # you can also use your own HTTPException
    elif not check_password_hash(user.hashedPw, password):
        print("wrong password")
        # print("wrong password", __passwdHash(password)[-8:], user.hashedPw[-8:], password, __passwdHash(password)[-8:])
        raise InvalidCredentialsException
    else:
        access_token = manager.create_access_token(
            data=dict(sub=name), expires=timedelta(hours=12)
        )
        # manager.set_cookie(data, access_token)
        return {'access_token': access_token, 'token_type': 'bearer'}

@app.get('/protected')
def protected_route(t = Depends(manager)):
    return {"message": "you are logged in!"}
## end login related stuff

def __passwdHash(passwd):
    return generate_password_hash(passwd, method='pbkdf2:sha512')

def stockNameCheck(stock):
    if "USDT" not in stock:
        stock += "USDT"
    return stock

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
    
@app.get("/getPortfolio", response_model = dict)
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

AMOUNTTYPES = ["amount", "currency"]
@app.post("/buyStock", response_model = dict)
async def buyStock(stockname : str, amount : float, amountType : str = "amount", current_user = Depends(manager)):
    if amountType not in AMOUNTTYPES:
        raise HTTPException(status_code=400, detail="amountType must be one of: " + str(AMOUNTTYPES) + " . amount means nr of stock, currency to buy for tha tmuch currency")
    
    stockname = stockNameCheck(stockname)
    # first check if we have enough cash
    portfolio = await getPortfolio(current_user.name)
    # print("current portfolio", portfolio)
    cash = portfolio["USDT"]
    currentPrice = __getCurrentPrice(stockname)
    # print("amount, currentPrice, cash ", amount, currentPrice, cash)
    cost = amount * currentPrice * (1 + COMMISSION)
    
    if cost >= cash:
        raise HTTPException(status_code=400, detail="Not enough cash. cost: %.2f$, cash: %.2f$" % (cost, cash))
    else:
        if stockname not in portfolio:
            portfolio[stockname] = amount
        else:
            # if we have some already
            portfolio[stockname] += amount
        portfolio["USDT"] = cash - cost
        db.update({"portfolio": portfolio}, Queryobject.name == current_user.name)
        return portfolio

@app.post("/sellStock", response_model = dict)
async def buyStock(stockname : str, amount : float = -1.,current_user = Depends(manager)):
    
    stockname = stockNameCheck(stockname)
    if amount < -1:
        raise HTTPException(status_code=400, detail="Invalid amount. has to be a positive number or empty for all")
    # first check if we have enough of that stock
    portfolio = await getPortfolio(current_user.name)
    # print("current portfolio", portfolio)
    holdingNr = portfolio.get(stockname)
    if amount == -1:
        amount = holdingNr # sell all mode
    
    if holdingNr is None:
        raise HTTPException(status_code=404, detail="Account does not have that stock")
    elif holdingNr < amount:
        raise HTTPException(status_code=400, detail="You do not own %.2f of %s. you own: %.2f" % (amount, stockname, holdingNr))
    
    currentPrice = __getCurrentPrice(stockname)
    
    win = amount * currentPrice * (1 - COMMISSION)
    portfolio[stockname] = holdingNr - amount
    if portfolio[stockname] == 0:
        del portfolio[stockname]
    portfolio["USDT"] = portfolio["USDT"] + win
    db.update({"portfolio": portfolio}, Queryobject.name == current_user.name)
    
    return portfolio
    
def __getStringNow():
    return __codeTimestamp(datetime.utcnow())
    
def __codeTimestamp(stringTS):
    return datetime.strftime(stringTS, "%Y-%m-%dT%H:%M:%S")

def __decodeTimestamp(timestamp):
    return datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S")
    
def __getBinancePrice(symbol):
    try:
        price = float(client.get_avg_price(symbol=symbol)["price"])
        return price
    except BinanceAPIException as e:
        print("BinanceAPIException for symbol: " + str(symbol))
        raise e

def __getCurrentPrice(symbol):
    # symbol has to be like BTCUSDT
    # try to save querying the api with lookup
    # handle non direct lookups
    symbol = stockNameCheck(symbol)
    
    if symbol == "USDT":
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
    
    if price != 0. and price is not None:
        # last check
        return price
    else:
        raise Exception("uhoh, price is 0. somehow, something went wrong!")
    
@app.get("/currentPrice", response_model = float)
async def getCurrentPrice(symbol: str):
    return __getCurrentPrice(symbol)


if __name__ == "__main__":
    uvicorn.run("acchandler:app", host="0.0.0.0", log_level="debug")