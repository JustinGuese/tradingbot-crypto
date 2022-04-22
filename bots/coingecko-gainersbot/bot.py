from bs4 import BeautifulSoup
from cloudscraper import create_scraper
from os import environ
from tradinghandler.trading import TradingInteractor

def extractOne(item):
    Symbol = item.find("span",{"class":"tw-hidden d-lg-inline font-normal text-3xs mt-1"}).text.strip()
    Volume = item.find("td",{"class":"td-liquidity_score lit"}).text.strip()
    Price = item.find("td",{"class":"td-price price"}).text.strip()
    per = item.find("td",{"class":"change24h"}).text.strip()
    return (Symbol,Volume.replace("$",''),Price.replace("$",''),per.replace("%",''))

def getCoingeckoTrending():
    url = "https://www.coingecko.com/en/coins/trending?time=%s&top=%d" % (environ.get("COINGECKO_LOOKBACK","d30"), int(environ.get("COINGECKO_TOP",100)))
    
    scraper = create_scraper()
    response = scraper.get(url)
    soup = BeautifulSoup(response.text,'lxml')
    allHtmls = soup.find("table",{"id":"gecko-table-all"}).find("tbody").find_all("tr")
    print("found %d entries" % len(allHtmls))
    results = []
    for item in allHtmls:
        results.append(extractOne(item))
    # with Pool() as pool:
    #     main = pool.map(extractOne,allHtmls).get()
    return results
        
        
coins = getCoingeckoTrending()

ti = TradingInteractor(environ["BOTNAME"])
portfolio = ti.getPortfolio()
usdt = portfolio["USDT"]

trendingCoins = [x[0] + "USDT" for x in coins]

# first sell all that are not trending anymore
for coin in portfolio:
    if coin not in trendingCoins and coin != "USDT":
        print("selling: %s" % coin)
        ti.sell(coin,-1)
# then get current balance again
portfolio = ti.getPortfolio()
usdt = portfolio["USDT"]

# and buy all 
startBuyMoney = usdt / 5 # start with a 4th
for i,coin in enumerate(trendingCoins):
    if coin not in portfolio and startBuyMoney > 10:
        print("pos %d: buying %.2f$ of %s" % (i+1, startBuyMoney, coin))
        try:
            ti.buy(coin,startBuyMoney)
            startBuyMoney *= .75 # half the invest
        except Exception as e:
            print("problem buying %s. skip" % coin)