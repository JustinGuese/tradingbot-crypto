from pymongo import MongoClient
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

mongoclient = MongoClient("mongodb://%s:27017" % environ["MONGODB_HOST"])
tradingdb = mongoclient.tradingdb
lastPricesCol = tradingdb.lastPrices
accountsCol = tradingdb.accounts
tradesCol = tradingdb.trades
errorsCol = tradingdb.errors

app = FastAPI()


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
    res = accountsCol.find_one({"name": name})
    if res is None:
        return None
    else:
        return Account(**res)
    
def logTrade(stock, amount, price, direction, account):
    if direction not in ["buy", "sell"]:
        raise HTTPException(status_code=400, detail="Invalid direction. has to be buy or sell")
    trade = {
        "stockname" : stock,
        "amount" : amount,
        "price" : round(price,2),
        "volume" : round(amount * price, 2),
        "direction" : direction,
        "account" : account,
        "timestamp" : __getStringNow()
    }
    tradesCol.insert_one(trade)

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
    res = accountsCol.find_one({"name": account.name})
    if not res is None:
        raise HTTPException(status_code=400, detail="Account already exists")
    else:
        account.hashedPw = __passwdHash(account.hashedPw)
        accountsCol.insert_one(jsonable_encoder(account))
        return account
    
@app.get("/getPortfolio", response_model = dict)
async def getPortfolio(accountName: str):
    res = accountsCol.find_one({"name": accountName})
    if res is None:
        raise HTTPException(status_code=404, detail="Account does not exists")
    else:
        return res["portfolio"]
    
@app.get("/getPortfolioWorth", response_model = float)
async def getPortfolioWorth(accountName: str):
    res = accountsCol.find_one({"name": accountName})
    if res is None:
        raise HTTPException(status_code=404, detail="Account does not exists")
    else:
        portfolio = res["portfolio"]
        print("portfolio", portfolio)
        total = 0.
        for item in portfolio:
            total += float(item["amount"]) * __getCurrentPrice(item["symbol"])
        return total
    
@app.get("/getAllAccounts", response_model = List[Account])
async def getAllAccounts():
    # return db.all()
    resp = []
    cursor = accountsCol.find({})
    for acc in cursor:
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
        accountsCol.update_one({"name": current_user.name}, {"$set": {"portfolio": portfolio}})
        logTrade(stockname, amount, currentPrice, "buy", current_user.name)
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
    accountsCol.update_one({"name": current_user.name}, {"$set": {"portfolio": portfolio}})
    logTrade(stockname, amount, currentPrice, "sell", current_user.name)
    
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
    
    res = lastPricesCol.find_one({"symbol": symbol})
    price = 0.
    if res is not None:
        # if it is there check the timestamp
        if __decodeTimestamp(res["timestamp"]) + timedelta(minutes=PRICEQUERYCACHE) > datetime.utcnow():
            price = float(res["price"])
        else: # we have to update current price
            price = __getBinancePrice(symbol)
            upd = {'price': price, 'timestamp': __getStringNow()}
            lastPricesCol.update_one({"symbol": symbol}, {"$set": upd})
    else: # we have to create the entry
        price = __getBinancePrice(symbol)
        js = {'symbol': symbol, 'price': price, 'timestamp': __getStringNow()}
        lastPricesCol.insert_one(js)
    
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