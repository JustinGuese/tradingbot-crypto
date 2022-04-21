FROM python:slim
RUN mkdir -p /persistent/models/
RUN apt update && apt install -y git
RUN pip install git+https://github.com/JustinGuese/tradingbot-crypto-interactor
COPY ./src/requirements.txt /
RUN pip install -r requirements.txt
COPY ./src/train.py /
COPY ./src/app.py /
CMD ["python", "/app.py"]