#!/bin/bash
docker build -t guestros/tradingbot-aperanksimple:latest ./aperankbot
docker push guestros/tradingbot-aperanksimple:latest
# coingecko trending
docker build -t guestros/tradingbot-coingeckotrending:latest ./coingeckoRankDaily
docker push guestros/tradingbot-coingeckotrending:latest