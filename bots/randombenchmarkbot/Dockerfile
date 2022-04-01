FROM python:slim
RUN apt update && apt install -y git
RUN pip install git+https://github.com/JustinGuese/tradingbot-crypto-interactor
COPY requirements.txt /
RUN pip install -r requirements.txt
COPY bot.py /bot.py
CMD ["python", "/bot.py"]