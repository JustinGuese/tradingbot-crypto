import requests
from os import environ

res = requests.get("https://api.cryptoqualitysignals.com/v1/getSignal/?api_key=62627172E7461&interval=20").json()
print(res)