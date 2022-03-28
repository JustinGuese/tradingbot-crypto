#!/bin/bash
docker build -t guestros/tradingbot-aperanksimple:latest ./aperankbot
docker push guestros/tradingbot-aperanksimple:latest
# coingecko trending
docker build -t guestros/tradingbot-coingeckotrending:latest ./coingeckoRankDaily
docker push guestros/tradingbot-coingeckotrending:latest
# simpleSma golden cross
docker build -t guestros/tradingbot-simplesma-goldencross:latest ./simpleSMACross
docker push guestros/tradingbot-simplesma-goldencross:latest