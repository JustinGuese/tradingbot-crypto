from fastapi import FastAPI, HTTPException
from db import accountsDB, tradesDB, errorsDB, pricehistoryDB, \
    Account, Trade, Error, PriceHistory, socialRankDB
from binance import Client
from typing import List, Dict
from os import environ
import pandas as pd
from dotenv import load_dotenv
from requests import get, post
from datetime import datetime, timedelta
load_dotenv() 
import uvicorn

app = FastAPI()

binanceapi = None
SYMBOLS = []

@app.on_event("startup")
def startup_event():
    binanceapi = Client(environ["BINANCE_KEY"], environ["BINANCE_SECRET"])

    environ["SYMBOLS"] = "BTC,ETH,MATIC,POL,AVAX,XRP,BNB,LINK,ADA"
    SYMBOLS = environ["SYMBOLS"].split(",")
    SYMBOLS = [symb + "USDT" for symb in SYMBOLS]
    # also check with DB to make sure we have everything
    uniqueSymbols = pricehistoryDB.distinct("symbol")
    for symbol in uniqueSymbols:
        if symbol not in SYMBOLS:
            try:
                # pricehistoryDB.insert_many(getHistoricPrices(symbol).to_dict("records"))
                SYMBOLS.append(symbol) # add that symbol from the db
            except Exception as e:
                # print(e)
                print("startup: Failed to get historic prices for symbol: " + symbol)

# checks if account exists and returns it if it does
def getAccount(name: str):
    account = accountsDB.find_one({"name": name})
    if account is not None:
        raise HTTPException(status_code=404, detail="Account not found")
    return account

@app.put("/accounts/{name}")
def create_account(name: str, startmoney: float = 10000.):
    # check if account exists
    account = accountsDB.find_one({"name": name})
    if account is not None:
        raise HTTPException(status_code=409, detail="Account already exists")
    # create account
    portfolio = {
        "USDT": startmoney,
    }
    account = Account(name=name, portfolio=portfolio)
    accountsDB.insert_one(account.dict())
    return account

@app.get("/portfolio/{name}", response_model = Dict[str, float])
def get_portfolio(name: str):
    account = getAccount(name)
    return account["portfolio"]

@app.get("/symbolcheck/{symbol}")
def check_symbol(symbol: str):
    try:
        info = binanceapi.get_symbol_info(symbol)
        if info is None:
            return False
        else:
            return info
    except:
        return False

def getHistoricPrices(symbol, interval = "60m", lookback = "2 hour ago UTC"):
    if interval == "1m":
        interval = Client.KLINE_INTERVAL_1MINUTE
    elif interval == "60m":
        interval = Client.KLINE_INTERVAL_1HOUR
    elif interval == "30m":
        interval = Client.KLINE_INTERVAL_30MINUTE
    elif interval == "1d":
        interval = Client.KLINE_INTERVAL_1DAY
    else:
        raise ValueError("Invalid interval, only 1m, 30m 60m 1d supported")
    klines = binanceapi.get_historical_klines(symbol, interval, lookback)
    hist_df = pd.DataFrame(klines)
    hist_df.columns = ['opentime', 'open', 'high', 'low', 'close', 'volume', 'Close Time', 'Quote Asset Volume', 
                    'nrTrades', 'tbbasevolume', 'tbquotevolume', 'Ignore']
    hist_df['opentime'] = pd.to_datetime(hist_df['opentime']/1000, unit='s')
    hist_df['Close Time'] = pd.to_datetime(hist_df['Close Time']/1000, unit='s')
    hist_df = hist_df[['opentime', 'open', 'high', 'low', 'close', 'volume','nrTrades', 'tbbasevolume', 'tbquotevolume']]
    for col in ['open', 'high', 'low', 'close','volume','tbbasevolume', 'tbquotevolume']:
        hist_df[col] = hist_df[col].astype(float)
    for col in ['nrTrades']:
        hist_df[col] = hist_df[col].astype(int)
    hist_df["symbol"] = symbol
    return hist_df

@app.get("/update/price")
def update():
    for symbol in SYMBOLS:
        try:
            histDF = getHistoricPrices(symbol)
        except Exception as e:
            print("problem with symbol " + symbol  + ": " + str(e))
            continue
        # write only those to DB that are not already in there
        pricehistoryDB.insert_many(histDF.to_dict(orient="records"))

@app.get("/update/priceBig")
def bigUpdate():
    for symbol in SYMBOLS:
        try:
            histDF = getHistoricPrices(symbol, lookback="5 year ago UTC")
        except Exception as e:
            print("problem with symbol " + symbol  + ": " + str(e))
            continue
        # write only those to DB that are not already in there
        pricehistoryDB.insert_many(histDF.to_dict(orient="records"))

# apewisdom
@app.get("/update/apewisdom/")
def apewisdom():
    jsdata = get("https://apewisdom.io/api/v1.0/filter/all-crypto/").json()["results"]
    update = { str(datetime.utcnow()) : jsdata }
    socialRankDB.insert_one(update)

# get price data
@app.get("/priceHistoric/{symbol}/{lookbackdays}")
def getPriceHistoric(symbol: str, lookbackdays: int = 1):
    lookback = datetime.utcnow() - timedelta(days=lookbackdays)
    hist = pricehistoryDB.find({"symbol": symbol, "opentime": {"$gte": lookback}})
    hist = [elm for elm in hist]
    if len(hist) == 0:
        # raise HTTPException(status_code=404, detail="Price history not found")
        # download data for that symbol
        SYMBOLS.append(symbol)

    hist = pd.DataFrame(hist)
    hist = hist.set_index("opentime")
    hist.drop(["_id"], axis=1, inplace=True)
    return hist.to_dict()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0")