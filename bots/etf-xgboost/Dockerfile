FROM python:slim
RUN apt update && apt install -y git
RUN pip install git+https://github.com/JustinGuese/tradingbot-crypto-interactor
RUN mkdir -p /persistent
COPY ./src/requirements.txt /
RUN pip install -r requirements.txt
COPY ./src/train.py /train.py
COPY ./src/bot.py /bot.py
CMD ["python", "/bot.py"]