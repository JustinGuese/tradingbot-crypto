from requests import get
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from os import environ
from datetime import datetime
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.dialects.postgresql import insert


# environ["PSQL_URL"] = 
DATABASE_URL = "postgresql+psycopg2://" + environ["PSQL_URL"] # user:password@postgresserver/db
engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(engine)

Base = declarative_base()
class BinanceRecentTrade(Base):
    __tablename__ = "binance_recentTrades"
    id = Column(Integer, primary_key=True)
    time = Column(DateTime)
    symbol = Column(String)
    price = Column(Float)
    qty = Column(Float)
    quoteQty = Column(Float)
    isBuyerMaker = Column(Boolean)
    isBestMatch = Column(Boolean)

def oneGet(symbol, batchsize):
    recentTrades = get('https://api.binance.com/api/v3/trades?limit=%s&symbol=%s' % (str(batchsize), symbol), timeout = 3).json()
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
    df["symbol"] = symbol
    # df = df.set_index("id")
    for col in ["price", "qty", "quoteQty"]:
        df[col] = df[col].astype(float)
    # then create a lot of objects
    dictionary = df.to_dict(orient="records")
    tradeobjects = []
    # for obj in dictionary:
    #     tradeobjects.append(BinanceRecentTrade(**obj))
    # then write to sql
    with Session() as s:
        sqlinstructs = []
        for obj in dictionary:
            s.execute(insert(BinanceRecentTrade)
                .values(obj)
                .on_conflict_do_nothing())
        s.commit()


Base.metadata.create_all(engine)

count = 0
time = datetime.now()
SYMBOL = "AVAXUSDT"
batchsize = 1000
try:
    while True:
        oneGet(SYMBOL, batchsize)
        count += batchsize
        if count / 100000 == 1:
            batchsize = 20
        if count % 100000 == 0:
            took = datetime.now() - time
            took = took.total_seconds()
            ps = count / took
            print("got {} entries in {} s. {} p/s".format(count, took, ps))
        # raise ValueError("stop bc we need to set id unique")
except KeyboardInterrupt:
    print('interrupted!')