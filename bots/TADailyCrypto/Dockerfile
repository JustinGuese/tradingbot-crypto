FROM python:slim
RUN apt update && apt install -y git
RUN pip install git+https://github.com/JustinGuese/tradingbot-crypto-interactor
COPY bot.py /bot.py
CMD ["python", "/bot.py"]