FROM python:3.9-slim
RUN apt update && apt install -y git
RUN pip install git+https://github.com/JustinGuese/tradingbot-crypto-interactor
RUN mkdir -p /results/
COPY requirements.txt /
RUN pip install -r requirements.txt
COPY training.py /training.py
COPY bot.py /bot.py
CMD ["python", "/bot.py"]