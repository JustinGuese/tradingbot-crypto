import requests 
from os import environ
from glassnode import GlassnodeClient
from time import sleep
import pandas as pd
from datetime import datetime
from tqdm import tqdm
import json

SYMBOLS = ["ETH", "BNB", "XRP", "SOL", "AVAX", "LUNA", "ADA"]

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

try:
    with open("noworky.json", "r") as file:
        NOWORKY = json.load(file)
except:
    NOWORKY = dict()

takes = len(INDICATORS) * len(SYMBOLS) * 2  / 60 # seconds
print("will take %.2f minutes" % takes)

for symbol in tqdm(SYMBOLS):
    res = None
    failed = []
#     # 30 requests a min max
    for indicator in INDICATORS:
        # first check if its proven to work or not
        skip = False
        if NOWORKY.get(symbol) is not None:
            if indicator in NOWORKY[symbol]:
                failed.append(indicator)
                skip = True
        if not skip:
            start = datetime.now()
            try:
                resp = getinfo(BASEAPIURL + indicator, symbol)
                if len(resp) > 0:
                    if indicator == "pi_cycle_top":
                        # returns special values
                        
                        resp2 = pd.json_normalize(resp)
                        resp2.index = resp.index
                        resp = resp2

                    resp = resp.add_prefix(indicator + '_')
                    if res is None:
                        # let first response be df
                        res = resp
                    else:
                        # merge dfs on index (timestamp)
                        res = pd.merge(res, resp, left_index=True, right_index=True)
                else:
                    failed.append(indicator)
            except Exception as e:
                print("error with: skip %s" % indicator)
                print(e)
                failed.append(indicator)
                NOWORKY[symbol] = NOWORKY.get(symbol, []) + [indicator]
            took = (datetime.now() - start).total_seconds()
            if took < 2:
                pausefor = 2 - took
                sleep(pausefor)
    # symbol done
    # handle failed
    if res is not None:
        for col in failed:
            res[col] = None
        res.to_csv("results/data_%s.csv" % symbol)
        print(res.head())
        print(res.describe())

# and write noworky to disk
with open("noworky.json", "w") as f:
    json.dump(NOWORKY, f, indent = 4)
