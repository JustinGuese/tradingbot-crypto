#!/bin/bash
docker build -t guestros/tradingbot-aperanksimple:latest ./aperankbot
docker push guestros/tradingbot-aperanksimple:latest
# coingecko trending
docker build -t guestros/tradingbot-coingeckotrending:latest ./coingeckoRankDaily
docker push guestros/tradingbot-coingeckotrending:latest
# simpleSma golden cross
docker build -t guestros/tradingbot-simplesma-goldencross:latest ./simpleSMACross
docker push guestros/tradingbot-simplesma-goldencross:latest
# complexSMA
docker build -t guestros/tradingbot-retrain-sma:latest ./calculatedSMACross
docker push guestros/tradingbot-retrain-sma:latest
# complexSMA + rsi
docker build -t guestros/tradingbot-retrain-sma-rsi:latest ./rsiSmaBot
docker push guestros/tradingbot-retrain-sma-rsi:latest
# basic rsi
docker build -t guestros/tradingbot-rsisimple:latest ./rsisimplecross
docker push guestros/tradingbot-rsisimple:latest