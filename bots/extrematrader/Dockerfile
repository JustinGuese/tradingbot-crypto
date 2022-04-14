FROM python:slim
RUN apt update && apt install -y git
RUN pip install git+https://github.com/JustinGuese/tradingbot-crypto-interactor
COPY ./src/requirements.txt /
RUN pip install -r requirements.txt
COPY ./src/extrematrader.py /extrematrader.py
CMD ["python", "/extrematrader.py"]