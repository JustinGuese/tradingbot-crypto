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
# lstm
docker build -t guestros/tradingbot-lstmlookback:latest ./lstm
docker push guestros/tradingbot-lstmlookback:latest
# randombot
docker build -t guestros/tradingbot-randombenchmark:latest ./randombenchmarkbot
docker push guestros/tradingbot-randombenchmark:latest
# lstm complexi with recent trades
docker build -t guestros/tradingbot-recentrades-lstm:latest ./lstm-recenttrades
docker push guestros/tradingbot-recentrades-lstm:latest
# xgb 30 min min max
docker build -t guestros/tradingbot-xgb-minmax-30min:latest ./xgb_minmaxima
docker push guestros/tradingbot-xgb-minmax-30min:latest
# coingecko gainers
docker build -t guestros/tradingbot-coingecko-gainers:latest ./coingecko-gainersbot
docker push guestros/tradingbot-coingecko-gainers:latest
# cryptoqualitysignalsbot and updater
docker build -t guestros/tradingbot-cryptoqualitysignalsbot-and-updater:latest ./cryptoqualitysignalsbot
docker push guestros/tradingbot-cryptoqualitysignalsbot-and-updater:latest
# etf xgboost
docker build -t guestros/tradingbot-etf-xgboost:latest ./etf-xgboost
docker push guestros/tradingbot-etf-xgboost:latest