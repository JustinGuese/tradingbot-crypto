from requests import get
import pandas as pd
from sqlalchemy import create_engine
from os import environ
from datetime import datetime

environ["PSQL_URL"] = "postgres:tradingbot@192.168.178.36:30001/postgres"
DATABASE_URL = "postgresql+psycopg2://" + environ["PSQL_URL"] # user:password@postgresserver/db
engine = create_engine(DATABASE_URL, echo=False)

def oneGet():
    recentTrades = get('https://api.binance.com/api/v3/trades?limit=1000&symbol=AVAXUSDT').json()
    # first price, second qty
    # {'id': 163589487,
    #   'isBestMatch': True,
    #   'isBuyerMaker': False,
    #   'price': '97.03000000',
    #   'qty': '0.78000000',
    #   'quoteQty': '75.68340000',
    #   'time': 1649055133603},
    df = pd.DataFrame(recentTrades)
    # df["time"] =  df["time"].apply(timeStampify)
    df["time"] =  pd.to_datetime(df["time"], unit='ms')
    df = df.set_index("id")
    for col in ["price", "qty", "quoteQty"]:
        df[col] = df[col].astype(float)
    df.to_sql("binance_recentTrades", engine, if_exists="append")

count = 0
time = datetime.now()
try:
    while True:
        oneGet()
        count += 1000
        if count % 100000 == 0:
            took = datetime.now() - time
            took = took.total_seconds()
            ps = count / took
            print("got {} entries in {} s. {} p/s".format(count, took, ps))
except KeyboardInterrupt:
    print('interrupted!')