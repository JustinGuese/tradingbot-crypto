#!/bin/bash
docker build -t guestros/tradingbot-recenttrades-ingestor:latest .
docker push guestros/tradingbot-recenttrades-ingestor:latest