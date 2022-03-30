from datetime import datetime
from training import doTraining, ti
from os import environ
from pathlib import Path
import pandas as pd

environ["SYMBOLS"] = "AVAXUSDT,BNBUSDT,ETHUSDT,XRPUSDT" # debug
SYMBOLS = environ["SYMBOLS"].split(",")

# check if we have to retrain
my_file = Path("./results/bestCombinations.csv")
if my_file.is_file():
    combs = pd.read_csv("./results/bestCombinations.csv")
    # check if retraining required
    lastTrainingDate = combs.iloc[0]["timestamp"]
    if datetime.utcnow().day == 0 and lastTrainingDate.month != datetime.utcnow().month:
        print("last training is a month ago, retrain now!")
        doTraining(SYMBOLS)
else:
    print("no training done, retrain now!")
    doTraining(SYMBOLS)
    combs = pd.read_csv("./results/bestCombinations.csv")

def checkCross(symbol, smallSMA, bigSMA):
    # get data
    # 24 hours in a day, so to get 200 we need to get the last 200 days
    # 200 hours are 8.33 days
    lookback = int(bigSMA / 24 * 1.25) # add 25% tolerance
    data = ti.getData(symbol, lookback=lookback)
    retries = 0
    while len(data) < bigSMA and retries < 3:
        lookback = int(lookback * 1.25)
        # print("retry lookback: ", lookback)
        data = ti.getData(symbol, lookback=lookback)
        retries += 1
    if retries >= 3:
        pd.set_option('display.max_colwidth', None)
        print(lookback)
        print(data.iloc[0])
        raise ValueError("max retries exceeded to get data length of df is less than minimum... is: ", len(data))
    data['smallSMA'] = data["close"].rolling(smallSMA).mean()
    data['bigSMA'] = data["close"].rolling(bigSMA).mean()
    # newest values are at the top, little weird
    # check if we have a cross
    print("current position of %s. smallSMA %.2f and bigSMA %.2f is upwardstrend? " % (symbol, data.iloc[-1]['smallSMA'], data.iloc[-1]['bigSMA']), data.iloc[-1]['smallSMA'] > data.iloc[-1]['bigSMA'])
    if data.iloc[-1]['smallSMA'] > data.iloc[-1]['bigSMA'] and data.iloc[-2]['smallSMA'] <= data.iloc[-2]['bigSMA']:
        return "upcross", True
    elif data.iloc[-1]['smallSMA'] < data.iloc[-1]['bigSMA'] and data.iloc[-2]['smallSMA'] >= data.iloc[-2]['bigSMA']:
        return "downcross", False
    else: 
        return "nocross", data.iloc[-1]['smallSMA'] > data.iloc[-1]['bigSMA']

portfolio = ti.getPortfolio()
usdt = portfolio["USDT"]
for i in range(len(combs)):
    symbol = combs.iloc[i]["symbol"]
    smallSma = int(combs.iloc[i]["smallSMA"])
    bigSma = int(combs.iloc[i]["bigSMA"])

    try:
        cross, positionUp = checkCross(symbol, smallSma, bigSma)
        sell = []
        buy = []
        if portfolio.get(symbol) is None:
            if positionUp:
                print("buying " + symbol)
                buy.append(symbol)
                # ti.buy(symbol, usdt / len(SYMBOLS) * 0.95) # buy 95% of usdt / number of symbols
        else:
            if not positionUp:
                # sell
                nrHolding = portfolio.get(symbol, 0)
                if nrHolding > 0:
                    print("selling " + symbol)
                    # ti.sell(symbol, -1) # sell all we have
                    sell.append(symbol)
        # first sell
        if len(sell) > 0:
            for symbol in sell:
                ti.sell(symbol, -1)
            portfolio = ti.getPortfolio()
            print(portfolio)
            usdt = portfolio["USDT"]
        # then buy
        if len(buy) > 0:
            for symbol in buy:
                ti.buy(symbol, usdt / len(buy) * 0.95)

    except Exception as e:
        print("problem with: " + symbol + " " + str(e))
        raise
