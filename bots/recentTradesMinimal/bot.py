from tradinghandler.trading import TradingInteractor
import joblib
import numpy as np
from pathlib import Path
from subprocess import call

if not Path("results/modelavax.pickle").is_file():
    print("!! first startup, need to copy all from resultsfirst directory into results")
    call("rsync -r ./resultsfirst/ ./results/", shell=True)

ti = TradingInteractor("test")
model = joblib.load("results/modelavax.pickle")

portfolio = ti.getPortfolio()

with open("results/bestcombination.csv", "r") as file:
    _ = file.readline()
    lookback,minhold,win = file.readline().split(",")
lookback,minhold,win = float(lookback),float(minhold),float(win)
lookback,minhold,win = int(lookback),int(minhold),int(win)

print("using values: ", lookback, minhold, win)

holdcnt = 0

try:
    while True:
        # get latest
        data = ti.getBinanceRecentTrades("AVAXUSDT", 1)
        # add data
        data['price_SMA5'] = data["price"].rolling(5).mean()
        data['price_SMA10'] = data["price"].rolling(10).mean()
        data['qty_SMA5'] = data["qty"].rolling(5).mean()
        data['qty_SMA10'] = data["qty"].rolling(10).mean()

        data["pricechange"] = data["price"].pct_change()
        data["quantitychange"] = data["qty"].pct_change()
        data["targetshift"] = data["pricechange"].shift(-5) # maybe it has an effect later
        data = data.fillna(0)
        # X = data.to_numpy()
        data.replace(np.inf, 999, inplace=True)
        data.replace(-np.inf, -999, inplace=True)
        data.drop(["time","symbol"], inplace = True, axis = 1)

        data = data.iloc[-(len(data) - 20) :]
        predictions = model.predict(data)

        crntPred = np.median(predictions[len(data)-lookback : len(data)])

        if crntPred == 1 and portfolio.get("AVAXUSDT", 0) == 0:
            print("BUY AVAX for $: ", portfolio.get("USDT"))
            portfolio = ti.buy("AVAXUSDT", portfolio.get("USDT")) # all in digga
            holdcnt = 0
        elif holdcnt >= minhold and crntPred == -1 and portfolio.get("AVAXUSDT", 0) > 0:
            print("SELL AVAX amount: ", portfolio.get("AVAXUSDT"))
            portfolio = ti.sell("AVAXUSDT", -1)
            holdcnt = 0
        # else:
        #     print("hodl!")

        holdcnt += 1
except KeyboardInterrupt:
    print('interrupted!')
