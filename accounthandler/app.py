from fastapi import FastAPI, HTTPException, Depends
from db import SessionLocal, engine, Base, \
    AccountPD, TradePD, ErrorPD, PriceHistory, \
    Account, Trade, Error, PriceHistory, ApeRank, CoinGeckoTrending, \
        PortfolioTracker, FearGreedIndex, BinanceRecentTrade, TASummary, \
        StockData
from sqlalchemy.orm import Session
from binance import Client
from typing import List, Dict
from os import environ
import pandas as pd
from dotenv import load_dotenv
load_dotenv() 
from requests import get, post
from datetime import datetime, timedelta
import uvicorn
from hashlib import sha512
import json
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
import re
from tradingview_ta import TA_Handler, Interval
import yfinance as yf


Base.metadata.create_all(bind=engine)


# Dependency
def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


app = FastAPI()

binanceapi = Client(environ["BINANCE_KEY"], environ["BINANCE_SECRET"])
# environ["SYMBOLS"] = "BTC,ETH,MATIC,AVAX,XRP,BNB,LINK,ADA"
SYMBOLS = environ["SYMBOLS"].split(",")
SYMBOLS = [symb + "USDT" for symb in SYMBOLS]

STOCKS = environ["STOCKS"].split(",")
STOCKS = [symb + "USD" for symb in STOCKS]


# @app.on_event("startup")
# def startup_event():
# also check with DB to make sure we have everything
# uniqueSymbols = db.query.distinct(PriceHistory.symbol).all()
# for symbol in uniqueSymbols:
#     if symbol not in SYMBOLS:
#         try:
#             # pricehistoryDB.insert_many(getHistoricPrices(symbol).to_dict("records"))
#             SYMBOLS.append(symbol) # add that symbol from the db
#         except Exception as e:
#             # print(e)
#             print("startup: Failed to get historic prices for symbol: " + symbol)


# checks if account exists and returns it if it does
def getAccount(name: str, db):
    # db.query(models.Record).all()
    account = db.query(Account).filter(Account.name == name).first()
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return account

@app.put("/accounts/{name}")
def create_account(name: str, description: str = "", startmoney: float = 10000., db: Session = Depends(get_db)):
    # check if account exists
    account = db.query(Account).filter(Account.name == name).first()
    if account is not None:
        raise HTTPException(status_code=409, detail="Account already exists")
    # create account
    portfolio = {
        "USDT": startmoney,
    }
    account = Account(name=name, portfolio=portfolio, description=description, 
        lastTrade=datetime.utcnow(), netWorth = startmoney, lastUpdateWorth = datetime.utcnow())
    db.add(account)
    db.commit()
    return account

@app.get("/accounts/")
def getAccounts(db: Session = Depends(get_db)):
    return db.query(Account.name, Account.netWorth, Account.portfolio).order_by(Account.netWorth.desc()).all()

@app.post("/account/reset/{name}")
def resetAccount(name: str, db: Session = Depends(get_db)):
    account = getAccount(name, db)
    account.portfolio = {
        "USDT": 10000.,
    }
    account.netWorth = 10000.
    account.lastTrade = datetime.utcnow()
    account.lastUpdateWorth = datetime.utcnow()
    db.commit()
    return account

@app.get("/accounts/ranked/")
def getRankedAccounts(db: Session = Depends(get_db)):
    return db.query(Account.name, Account.netWorth, Account.lastTrade).order_by(Account.netWorth.desc()).all()

@app.get("/accounts/{name}")
def get_account(name: str, db: Session = Depends(get_db)):
    return getAccount(name, db)

@app.get("/portfolio/{name}", response_model = Dict[str, float])
def get_portfolio(name: str, db: Session = Depends(get_db)):
    account = getAccount(name, db)
    return account.portfolio

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

def createHistoricPriceId(row):
    return sha512((row["symbol"] + str(row["opentime"])).encode()).hexdigest()[:10]

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
    # then create id out of it
    hist_df["id"] = hist_df.apply(createHistoricPriceId, axis=1)
    return hist_df

def savePrice2DB(df, db):
    # write only those to DB that are not already in there
    bulk = []
    for i in range(len(df)):
        obj = PriceHistory(**df.iloc[i].to_dict())
        db.merge(obj)
    db.commit()

# @app.get("/update/price")
def update(db):
    print("geddin updates for: ", SYMBOLS)
    for symbol in SYMBOLS:
        try:
            histDF = getHistoricPrices(symbol)
            savePrice2DB(histDF, db)
        except Exception as e:
            print("problem with symbol " + symbol  + ": " + str(e))
            continue

# 
def __updatePortfolioWorth(db):
    symbolPrices = dict()
    allAccounts = db.query(Account).all()
    for account in allAccounts:
        netWorth = account.portfolio.get("USDT", 0.)
        for symbol, amount in account.portfolio.items():
            if symbol != "USDT":
                if symbol not in symbolPrices:
                    try:
                        symbolPrices[symbol] = getCurrentPrice(symbol)
                    except Exception as e:
                        raise Exception("problem with: " + symbol + ": " + str(e))
                netWorth += symbolPrices[symbol] * amount
        account.netWorth = netWorth
        account.lastUpdateWorth = datetime.utcnow()
        db.commit()
        # next add it to the portfolio db
        pt = PortfolioTracker(accountname = str(account.name), portfolioworth = float(account.netWorth), timestamp = datetime.utcnow())
        db.add(pt)
        db.commit()

@app.get("/update/portfolioworth")
def updatePortfolioWorth(db: Session = Depends(get_db)):
    __updatePortfolioWorth(db)

# this should only run daily
@app.get("/update24/coingecko/trending")
def updateCoingeckoTrending(db: Session = Depends(get_db)):
    # takes coingecko trending data and writes it to db
    headers = {'accept': 'application/json'}
    response = get('https://api.coingecko.com/api/v3/search/trending', headers=headers).json()["coins"]
    ts = datetime.utcnow()
    for rank, coin in enumerate(response):
        symbol = coin["item"]["symbol"]
        symbol += "USDT"
        existsCheck = check_symbol(symbol)
        if not existsCheck: # is false if not exists, so only continue here if it exists
            SYMBOLS.append(symbol)
            # but save it to DB as well
            # rank = Column(Integer)
            # ticker = Column(String(10))
            # timestamp = Column(DateTime)
            # marketcaprank = Column(Integer)
            cgt = CoinGeckoTrending(rank = rank, ticker = symbol, timestamp = ts, 
                marketcaprank = coin["market_cap_rank"])
            db.add(cgt)
    db.commit()


        

@app.get("/update/priceBig")
def bigUpdate(symbolSelection = SYMBOLS, db: Session = Depends(get_db)):
    for symbol in symbolSelection:
        try:
            histDF = getHistoricPrices(symbol, lookback="5 year ago UTC")
        except Exception as e:
            print("problem with symbol " + symbol  + ": " + str(e))
            continue
        savePrice2DB(histDF, db)

def apeTickerFix(ticker):
    return ticker.replace(".X", "USDT")

# apewisdom
# supposed to be executed daily
# @app.get("/update/apewisdom/")
def apewisdom(db):
    jsdata = get("https://apewisdom.io/api/v1.0/filter/all-crypto/").json()["results"]
    df = pd.DataFrame(jsdata)
    df.drop(["name", "rank_24h_ago", "mentions_24h_ago"], axis=1, inplace=True)
    df["ticker"] = df["ticker"].apply(apeTickerFix)
    df["timestamp"] = datetime.utcnow()
    for col in ["mentions", "upvotes", "rank"]:
        df[col] = df[col].astype(int)
    for i in range(len(df)):
        obj = ApeRank(**df.iloc[i].to_dict())
        db.merge(obj)
    db.commit()

@app.get("/data/apewisdom/{ticker}/{lookback}", tags = ["data"])
def apewisdomGet(ticker: str, lookback: int, db: Session = Depends(get_db)):
    return db.query(ApeRank).filter(ApeRank.ticker == ticker).filter(ApeRank.timestamp > datetime.utcnow() - pd.Timedelta(days = lookback)).all()

@app.get("/data/apewisdom/", tags = ["data"])
def apewisdomGetAll(db: Session = Depends(get_db)):
    return db.query(ApeRank).filter(ApeRank.timestamp > datetime.utcnow() - pd.Timedelta(hours = 1.5)).all()

@app.get("/data/feargreed/{lookback}", tags = ["data"])
def cnnsentiment(lookback: int = 1, db: Session = Depends(get_db)):
    return db.query(FearGreedIndex).filter(FearGreedIndex.timestamp > datetime.utcnow() - pd.Timedelta(days = lookback)).order_by(FearGreedIndex.timestamp.desc()).all()

@app.get("/data/stock/{symbol}/{lookback}", tags = ["data", "stock"])
def getStockData(symbol: str, lookback: int = 1, db: Session = Depends(get_db)):
    return db.query(StockData).filter(StockData.symbol == symbol).filter(StockData.date > datetime.utcnow() - pd.Timedelta(days = lookback)).order_by(StockData.date.desc()).all()

@app.get("/data/tasummary/{symbol}/{lookback}",  tags = ["data", "stock"])
def getTASummary(symbol: str, lookback: int = 1, db: Session = Depends(get_db)):
    return db.query(TASummary).filter(TASummary.symbol == symbol).filter(TASummary.timestamp > datetime.utcnow() - pd.Timedelta(days = lookback)).order_by(TASummary.timestamp.desc()).all()

## stock data functions
# @app.get("/data/updatestocks/")
def stockUpdateDaily(db):
    for stock in environ["STOCKS"].split(","):
        df = yf.download(stock, period="2d", interval="1d")
        df = df.reset_index()
        df["symbol"] = stock
        df.rename(columns={"Date" : "date" , "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}, inplace=True)
        df = df.drop(["Adj Close"], axis=1)

        for i in range(len(df)):
            obj = StockData(**df.iloc[i].to_dict())
            db.merge(obj)
        db.commit()

# ta summary
# id = Column(Integer, primary_key=True)
# symbol = Column(String)
# timestamp = Column(DateTime)
# recommendation = Column(String)
# buyCnt = Column(Integer)
# neutralCnt = Column(Integer)
# sellCnt = Column(Integer)
# @app.get("/data/updatestocks/tasummarycrypto")
def taUpdateCrypto(db):
    for stock in SYMBOLS:
        # stock += "USDT" # should alread be done above
        try:
            sta = TA_Handler(
                symbol=stock,
                screener="crypto",
                exchange="BINANCE",
                interval=Interval.INTERVAL_1_DAY,
                # proxies={'http': 'http://example.com:8080'} # Uncomment to enable proxy (replace the URL).
            )
            summary = sta.get_analysis().summary
            # Example output: {"RECOMMENDATION": "BUY", "BUY": 8, "NEUTRAL": 6, "SELL": 3}
            taobj = TASummary(symbol = stock, timestamp = datetime.utcnow(), recommendation = summary["RECOMMENDATION"], buyCnt = int(summary["BUY"]), neutralCnt = int(summary["NEUTRAL"]), sellCnt = int(summary["SELL"]))
            db.merge(taobj)
        except Exception as e:
            print( "taUpdateCrypto: problem with symbol " + stock + ": " + str(e))
    db.commit()

# @app.get("/data/updatestocks/tasummary")
def taUpdateStocks(db):
    for stock in STOCKS:
        try:
            stockpure = stock.replace("USD", "")
            sta = TA_Handler(
                symbol=stockpure,
                screener="america",
                exchange="NASDAQ",
                interval=Interval.INTERVAL_1_DAY,
                # proxies={'http': 'http://example.com:8080'} # Uncomment to enable proxy (replace the URL).
            )
            summary = sta.get_analysis().summary
            # Example output: {"RECOMMENDATION": "BUY", "BUY": 8, "NEUTRAL": 6, "SELL": 3}
            taobj = TASummary(symbol = stock, timestamp = datetime.utcnow(), recommendation = summary["RECOMMENDATION"], buyCnt = int(summary["BUY"]), neutralCnt = int(summary["NEUTRAL"]), sellCnt = int(summary["SELL"]))
            db.merge(taobj)
        except Exception as e:
            print( "stockUpdateCrypto: problem with symbol " + stock + ": " + str(e))
    db.commit()

# get price data
@app.get("/data/priceHistoric/{symbol}/{lookbackdays}", tags = ["data"])
def getPriceHistoric(symbol: str, lookbackdays: int = 1, db: Session = Depends(get_db)):
    lookback = datetime.utcnow() - timedelta(days=lookbackdays)
    hist = db.query(PriceHistory).filter(PriceHistory.symbol == symbol).filter(PriceHistory.opentime > lookback).all()
    if len(hist) == 0:
        # raise HTTPException(status_code=404, detail="Price history not found")
        # download data for that symbol
        SYMBOLS.append(symbol)
        # trigger update
        bigUpdate([symbol])
        # recursive call of this fct
        return getPriceHistoric(symbol, lookbackdays)
    hist = pd.DataFrame([h.__dict__ for h in hist])
    # print(hist.iloc[0])
    hist = hist.set_index("opentime")
    hist.drop(["id"], axis=1, inplace=True)
    return hist.to_dict()

## trade functioms

def getCurrentPrice(symbol):
    if "USDT" in symbol:
        return float(binanceapi.get_avg_price(symbol=symbol)["price"])
    elif "USD" in symbol:
        symbol = symbol.replace("USD", "")
        return float(yf.download(symbol, period="1d", interval="1m")["Close"][-1])
    else:
        raise ValueError("getCurrentPrice: symbol " + symbol + " not supported")
    

COMMISSION = 0.00125
@app.put("/buy/{name}/{symbol}/{amount}")
def buy(name: str, symbol: str, amount: float, amountInUSD: bool = True, db: Session = Depends(get_db)):
    account = getAccount(name, db)
    # portfolio = account.portfolio
    usdt = account.portfolio["USDT"]
    currentPrice = getCurrentPrice(symbol)
    if amountInUSD:
        amount = amount / currentPrice
    cost = currentPrice * amount * (1 + COMMISSION)
    if cost > usdt:
        raise HTTPException(status_code=400, detail="Not enough USDT. requires: %.2f$, you have %.2f$" % (cost, usdt))
    account.portfolio["USDT"] = usdt - cost
    account.portfolio[symbol] = account.portfolio.get(symbol, 0) + amount
    # account.portfolio = json.dumps(portfolio)
    db.merge(account)
    db.commit()
    return account.portfolio

def __sell(name, symbol, amount, amountInUSD, db):
    account = getAccount(name, db)
    # portfolio = account.portfolio
    amountSymbol = account.portfolio.get(symbol, 0)
    currentPrice = getCurrentPrice(symbol)
    if amountSymbol == 0:
        raise HTTPException(status_code=400, detail="No such symbol in portfolio. portfolio: %s" % str(account.portfolio))
    if amount == -1:
        # means sell all
        amount = amountSymbol
    elif amountInUSD:
        amount = amount / currentPrice
    if amount > amountSymbol:
        raise HTTPException(status_code=400, detail="Not enough %s. requires: %.4f, you have %.4f" % (symbol, amount, amountSymbol))
    
    win = amount * currentPrice * (1 - COMMISSION)
    account.portfolio[symbol] = amountSymbol - amount
    account.portfolio["USDT"] = account.portfolio.get("USDT", 0) + win
    if account.portfolio[symbol] == 0:
        del account.portfolio[symbol]
    # account.portfolio = account.portfolio
    db.merge(account)
    db.commit()
    return account.portfolio

# sell
@app.put("/sell/{name}/{symbol}/{amount}")
def sell(name: str, symbol: str, amount: float = -1, amountInUSD: bool = True, db: Session = Depends(get_db)):
    return __sell(name, symbol, amount, amountInUSD, db)

@app.post("/emergencyLiquidate/{name}")
def emergencyLiquidate(name: str, db: Session = Depends(get_db)):
    account = getAccount(name, db)
    portfolio = account.portfolio
    for symbol in portfolio:
        if symbol != "USDT":
            _ = __sell(name, symbol, -1, False, db)
    return account

def cnnextract(db):
    cnn = "https://money.cnn.com/data/fear-and-greed/"
    req = Request(url=cnn, headers = {"user-agent": "my-app/0.0.1"})

    response = urlopen(req)
    feargreedindex = dict()

    html = BeautifulSoup(response, features="html.parser")

    feargreedindex = html.find(id="needleChart")

    datarows = feargreedindex.findAll("li")
    datarows = [int(re.findall(r'[0-9]+', str(x))[-1]) for x in datarows]

    # print(datarows)
    datarows = [datetime.utcnow()] + datarows 
    #     id = Column(Integer, primary_key=True, index=True)
    # timestamp = Column(DateTime)
    # # "now", "yesterday", "1weekago", "1monthago", "1yearago"
    # now = Column(Integer)
    # yesterday = Column(Integer)
    # weekago = Column(Integer)
    # monthago = Column(Integer)
    # yearago = Column(Integer)
    df = pd.DataFrame([datarows], columns=["timestamp", "now", "yesterday", "weekago", "monthago", "yearago"])
    
    # then write to db
    fgiobj = FearGreedIndex(**df.iloc[0].to_dict())
    db.merge(fgiobj)
    db.commit()

@app.get("/data/feargreedindex/{lookbackdays}", tags = ["data"])
def feargreedindex(lookbackdays: int = 1, db: Session = Depends(get_db)):
    res = db.query(FearGreedIndex).filter(FearGreedIndex.timestamp > datetime.utcnow() - timedelta(days=lookbackdays)).all()
    return res

@app.get("/data/binancerecenttrades/{symbol}/{lookbackdays}", tags = ["data"])
def binancerecenttrades(symbol: str, lookbackdays: int = -1, db: Session = Depends(get_db)):
    if lookbackdays == -1:
        # get all the data we have
        res = db.query(BinanceRecentTrade).filter(BinanceRecentTrade.symbol == symbol).order_by(BinanceRecentTrade.id.desc()).all()
    else:
        res = db.query(BinanceRecentTrade).filter(BinanceRecentTrade.symbol == symbol).filter(BinanceRecentTrade.time > datetime.utcnow() - timedelta(days=lookbackdays)).order_by(BinanceRecentTrade.id.desc()).all()
    return res

## stock functions
# @app.get("/data/stock/tasummary/{symbol}")
# def getTaSummary(symbol: str, db: Session = Depends(get_db)):
#     res = db.query(TaSummary).filter(TaSummary.symbol == symbol).order_by(TaSummary.id.desc()).first()
#     return res

@app.get("/update/hourly/")
def hourlyUpdate(db: Session = Depends(get_db)):
    update(db) # prices update hourly
    apewisdom(db)
    __updatePortfolioWorth(db)

@app.get("/update/daily/")
def dailyUpdate(db: Session = Depends(get_db)):
    cnnextract(db)
    # stock functions
    stockUpdateDaily(db)
    try:
        taUpdateStocks(db)
    except Exception as e:
        print(repr(e))
    try:
        taUpdateCrypto(db)
    except Exception as e:
        print(repr(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0")