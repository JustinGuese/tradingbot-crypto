FROM python:slim
RUN apt update && apt install -y git
RUN pip install git+https://github.com/JustinGuese/tradingbot-crypto-interactor
RUN mkdir -p /persistent/
COPY requirements.txt /
RUN pip install -r requirements.txt
COPY train.py /train.py
COPY bot.py /bot.py
CMD ["python", "/bot.py"]