import requests 
from os import environ
from glassnode import GlassnodeClient
from time import sleep
import pandas as pd
from datetime import datetime
from tqdm import tqdm

SYMBOLS = ["ETH"]

gn = GlassnodeClient(environ["GLASSNODE_KEY"])

def getinfo(route, symbol):
    sopr = gn.get(
        route,
        a=symbol,
        s='2020-01-01',
        i='24h'
    )
    return sopr

BASEAPIURL = "https://api.glassnode.com/v1/metrics/indicators/"
INDICATORS = [
    'sopr_adjusted', 'rhodl_ratio', 'cvdd', "balanced_price_usd", "hash_ribbon",
    "difficulty_ribbon", "nvt", "nvts", "velocity", "puell_multiple",
    "reserve_risk", "hodler_net_position_change", "cyd_supply_adjusted", 
    "asol", "msol", "average_dormancy", "liveliness", "unrealized_profit",
    "stock_to_flow_ratio", "ssr", "ssr_oscillator", "soab", "sol_1h", "sol_more_10y",
    "svab", "bvin", "investor_capitalization", "pi_cycle_top"
    ]

takes = len(INDICATORS) * len(SYMBOLS) * 2 # seconds
print("will take %d seconds" % takes)

for symbol in SYMBOLS:
    res = None
#     # 30 requests a min max
    for indicator in tqdm(INDICATORS):
        start = datetime.now()
        if res is None:
            try:
                res = getinfo(BASEAPIURL + indicator, symbol)
                res = pd.DataFrame(res)
                res.columns = [indicator]
            except Exception as e:
                print("error with: skip %s" % indicator)
        else:  
            try:
                res[indicator] = getinfo(BASEAPIURL + indicator, symbol)
            except Exception as e:
                print("problem with: skip ", indicator)
        took = (datetime.now() - start).total_seconds()
        if took < 2:
            pausefor = 2 - took
            sleep(pausefor)
    # symbol done
    res.to_csv("data_%s.csv" % symbol)
