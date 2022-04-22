import requests
from os import environ
from db import CryptoQualitySignal, session
from datetime import datetime, timedelta
from tradinghandler.trading import TradingInteractor

res = requests.get("https://api.cryptoqualitysignals.com/v1/getSignal/?api_key=%s&interval=5" % environ["CQS_API_KEY"]).json()
print(res)

# direction will be SHORT or LONG (?)
# type is one of:
# SHORT TERM
# SHORT/MID TERM
# SCALPING
# MID TERM
# LONG TERM

# first save everything to database
for signal in res["signals"]:
    # int cast
    for col in ["id", "risk_level"]:
        signal[col] = int(signal[col])
    # float cast
    for col in ["buy_start", "buy_end", "target1", "target2", "target3", "stop_loss", "ask"]:
        signal[col] = float(signal[col])
    # datetime cast
    signal["timestamp"] = datetime.strptime(signal["timestamp"], "%Y-%m-%d %H:%M:%S")
    signal["created_at"] = datetime.utcnow()
    signal["executed"] = False
    # make sanity check of target1, target2 , target3
    if not (signal["target1"] < signal["target2"] < signal["target3"]):
        if signal["target1"] == 0:
            signal["target1"] = signal["buy_end"]
        # else set target2 to target1
        signal["target2"] = signal["target1"]
        if signal["target3"] < signal["target2"]:
            signal["target3"] = signal["target2"]
    signalObj = CryptoQualitySignal(**signal)
    session.merge(signalObj)
session.commit()


ti = TradingInteractor(environ["BOTNAME"])
portfolio = ti.getPortfolio()
usdt = portfolio["USDT"]

# then trade based on signals
# get current signals from database until seven days back, which are not executed yet and which are direction LONG
if usdt > 10:
    longSignals = session.query(CryptoQualitySignal).filter(CryptoQualitySignal.executed == False, CryptoQualitySignal.direction == "LONG", CryptoQualitySignal.timestamp > datetime.utcnow() - timedelta(days=7)).all()
    for signal in longSignals:
        # get the current price of that coin
        currency = signal.currency
        if currency == "USD":
            currency = "USDT"
        if "USD" in symbol:
            symbol = symbol.replace("USD", "USDT")
        else:
            symbol = signal.coin + currency
        # sometimes symbol has weird values
        # try to get price of symbol
        try:
            price = ti.getCurrentPrice(symbol)
        except Exception as e:
            print("could not get price for: %s" % symbol)
            price = -1
        if price != -1:
            # if we have a price
            # check if we are in range yet
            if signal.buy_start <= price <= signal.buy_end:
                # the moment to buy!
                try:
                    print("buy - buy zone reached: %s" % symbol)
                    ti.buy(symbol, usdt / 4)
                    signal.executed = True
                    signal.inExecution = True
                    session.merge(signal)
                except Exception as e:
                    print("could not buy: %s" % symbol)
    session.commit()

portfolio = ti.getPortfolio()
usdt = portfolio["USDT"]
# then we have to check if we already reached a target for the open ones
if len(portfolio) > 1:
    openTrades = session.query(CryptoQualitySignal).filter(CryptoQualitySignal.inExecution == True).all()
    print("currently having %d open trades." % len(openTrades))
    for signal in openTrades:
        # get the current price of that coin
        currency = signal.currency
        if currency == "USD":
            currency = "USDT"
        symbol = signal.coin + currency
        # sometimes symbol has weird values
        # try to get price of symbol
        try:
            price = ti.getCurrentPrice(symbol)
        except Exception as e:
            print("could not get price for: %s" % symbol)
            price = -1
        if price != -1:
            # first check if we crossed the stop_loss already
            if price < signal.stop_loss:
                # the moment to sell!
                try:
                    # try to calculate the profit level
                    if signal.stop_loss < signal.target1:
                        # means it is the real stop loss
                        reason = "stop_loss :("
                    elif signal.stop_loss < signal.target2:
                        reason= "target1 :) "
                    elif signal.stop_loss < signal.target3:
                        reason = "target2 :)) "
                    else:
                        reason = "unknown :x"
                    print("sell - %s reached: %s" % (reason,symbol))
                    ti.sell(symbol, usdt / 4)
                    signal.inExecution = False
                    session.merge(signal)
                except Exception as e:
                    print("could not sell: %s" % symbol)
            # then check if we crossed the target1 already and if so, mark it in db
            elif price >= signal.target1:
                # set the new stop_loss to target1
                signal.stop_loss = price
                session.merge(signal)
            # then check if we crossed target 2, if yes sell the f out of it
            elif price >= signal.target2:
                # set new stop_loss to target2
                signal.stop_loss = price
                session.merge(signal)
            elif price > signal.target3:
                # the moment to sell anyways!
                try:
                    print("sell - bigprofit!$$$ crossed targetlevel 3: %s" % symbol)
                    ti.sell(symbol, -1)
                    signal.inExecution = False
                    session.merge(signal)
                except Exception as e:
                    print("could not sell: %s" % symbol)