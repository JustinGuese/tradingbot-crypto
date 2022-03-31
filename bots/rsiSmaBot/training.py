
# coinsrankday
from os import environ
# simplsmahr
# environ["BOTNAME"] = "simplsmahr"
# looks at coinsrank dailies and buys top 10 ranks
from tradinghandler.trading import TradingInteractor
import numpy as np
import pandas as pd
from tqdm import tqdm
from datetime import datetime
from multiprocessing import Pool
from ta.momentum import rsi


ti = TradingInteractor(environ["BOTNAME"], url = "10.147.17.73")
portfolio = ti.getPortfolio()
usdt = portfolio["USDT"]


#  golden cross. When the 50 EMA moves above the 200 SMA,

def buySim(tmpdata, money, nrStocks, i):
    crntPrice = tmpdata.iloc[i]['close']
    amount = money / crntPrice * 0.99
    cost = amount * crntPrice * (1 + 0.00025) # binance fees
    boughtFor = cost
    boughtAtI = i
    money -= cost
    nrStocks += amount
    return boughtFor, boughtAtI, money, nrStocks

def sellSim(tmpdata, trades, money, nrStocks, i, boughtFor, boughtAtI):
    crntPrice = tmpdata.iloc[i]['close']
    win = nrStocks * crntPrice * (1 - 0.00025) # commission
    money += win
    nrStocks = 0
    heldfor = i - boughtAtI # days
    profit = win - boughtFor # profit
    if heldfor == 0:
        # print("heldfor is zero, shouldnt be i, boughtAtI" , i, boughtAtI)
        # happens if buying at the last step
        # equal to profit / 1
        trades.append(profit)
    else:
        trades.append(profit / heldfor) # profit per day helt for
    return trades, nrStocks, money

def oneSimulation(comb_tuple):
    data, smallSMA, bigSMA = comb_tuple
    tmpdata = data.copy()
    tmpdata['smaSmall'] = tmpdata["close"].rolling(smallSMA).mean()
    tmpdata['smaBig'] = tmpdata["close"].rolling(bigSMA).mean()
    nrStocks = 0
    startingMoney = 10000 # 10 k starting
    money = startingMoney #  10k starting
    boughtFor = 0
    boughtAtI = 0
    trades = []
    for i in range(len(data)):
        SMASmall, SMABig, rsi = tmpdata.iloc[i]['smaSmall'], tmpdata.iloc[i]['smaBig'], tmpdata.iloc[i]['rsi']
        if SMASmall > SMABig and nrStocks == 0 and rsi <= 30:
            # buy
            boughtFor, boughtAtI, money, nrStocks = buySim(tmpdata, money, nrStocks, i)

        elif SMASmall < SMABig and nrStocks > 0 and rsi >= 70:
            # sell
            trades, nrStocks, money = sellSim(tmpdata, trades, money, nrStocks, i, boughtFor, boughtAtI)
    # on last day sell if we have stocks
    if nrStocks > 0:
        trades, nrStocks, money = sellSim(tmpdata, trades, money, nrStocks, i, boughtFor, boughtAtI)
    
    totalWin = (money - startingMoney) / len(data) # to average it to the timestep
    # avg/median Trade per timestep (hour)
    if len(trades) > 0:
        avgTrade = np.mean(trades)
        medTrade = np.median(trades)
    else:
        avgTrade = 0
        medTrade = 0

    # we are working with hour data on crypto, so i wanna take it * 24 * 30 to get monthly averages
    totalWin *= 24 * 30
    pctWinPerMonth = totalWin / startingMoney * 100
    pctWinPerYear = pctWinPerMonth * 12 # 12 months
    avgTrade *= 24 * 30
    medTrade *= 24 * 30 
    nrTrades = len(trades)
    return smallSMA, bigSMA, round(totalWin, 2), round(pctWinPerMonth, 2), round(pctWinPerYear, 2), round(avgTrade, 2), round(medTrade, 2), nrTrades

def getBestCombination(symbol):
    # like training
    # get data
    # 24 hours in a day, so to get 200 we need to get the last 200 days
    data = ti.getData(symbol, lookback=60) # not a whole year
    data["rsi"] = rsi(data["close"], 14)
    if len(data) < 200:
        raise ValueError("length of df is less than minimum 200... is: ", len(data))
    # add some randomness as well
    smallSMAs = [2,5,10,20,50,100,200] + np.random.randint(150, size=10).tolist()
    bigSMAs = [3,5,20,30,80,200,150] + np.random.randint(400, size=10).tolist()
    allCombinations = []
    for small in smallSMAs:
        for big in bigSMAs:
            if big > small: # only go for long investments for now
                # we need to pass data copy as well
                allCombinations.append((data.copy(),small,big))
    # print("trying out %d combinations" % len(allCombinations))
    # print(smallSMAs, bigSMAs)

    results = []
    # 1.01 it/s, ~1:05 min for 67 combinations
    # map async brings it down to 10 seconds geeez, so like 6.7 it/s
    # do a map async
    start = datetime.utcnow()
    with Pool() as p:
        results = p.map_async(oneSimulation, allCombinations)
        results = results.get()
    took = datetime.utcnow() - start
    took = took.total_seconds()#
    # print("took %d seconds" % took)
    # p close should happen automatically here
    # for small,big in tqdm(allCombinations):
    #     totalWin, pctWinPerMonth, pctWinPerYear, avgTrade, medTrade, nrTrades = oneSimulation(data, small, big)
    #     results.append([small,big,totalWin,pctWinPerMonth,pctWinPerYear,avgTrade,medTrade, nrTrades])
    df = pd.DataFrame(results, columns=["smallSMA", "bigSMA", "totalWin", "pctWinPerMonth", "pctWinPerYear", "avgTrade", "medTrade", "nrTrades"])
    df = df.sort_values(by="medTrade", ascending=False)
    # df.to_csv("results/%s.csv" % symbol)
    # print(df.head())

    best = df.iloc[0]
    if best["totalWin"] > 0 and best["medTrade"] > 0:
        # print("best: ", best)
        return best.to_list()
    else:
        # check if second entry is better
        df = df.sort_values(by="totalWin", ascending=False)
        best = df.iloc[0]
        return best.to_list()

def doTraining(SYMBOLS):
    currentBest = []
    for symbol in tqdm(SYMBOLS):
        # get training best combination if not exists
        smallSma, bigSma, totalWin, pctWinPerMonth, pctWinPerYear, avgTrade, medTrade, nrTrades = getBestCombination(symbol)
        print(f'The best combination for {symbol} is {smallSma}, {bigSma} with a total win of {totalWin} and a win per month of {pctWinPerMonth}% and a win per year of {pctWinPerYear}%. medTrade: {medTrade} avgTrade: {avgTrade} nrTrades: {nrTrades}')
        currentBest.append([symbol, smallSma, bigSma, totalWin, pctWinPerMonth, pctWinPerYear, avgTrade, medTrade, nrTrades])
    # save to csv
    df = pd.DataFrame(currentBest, columns=["symbol", "smallSMA", "bigSMA", "totalWin", "pctWinPerMonth", "pctWinPerYear", "avgTrade", "medTrade", "nrTrades"])
    df["timestamp"] = datetime.utcnow()
    df.to_csv("results/bestCombinations.csv")
    print(df)

if __name__ == "__main__":
    environ["SYMBOLS"] = "AVAXUSDT,BNBUSDT,ETHUSDT,XRPUSDT" # debug
    SYMBOLS = environ["SYMBOLS"].split(",")
    doTraining(SYMBOLS)