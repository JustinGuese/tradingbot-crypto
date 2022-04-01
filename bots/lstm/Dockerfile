FROM python:3.9-slim
RUN apt update && apt install -y git rsync
RUN pip install git+https://github.com/JustinGuese/tradingbot-crypto-interactor
RUN mkdir -p /results/
RUN mkdir -p /resultsfirst/
COPY requirements.txt /
RUN pip install -r requirements.txt
COPY training.py /training.py
COPY ./results/ /resultsfirst/
COPY bot.py /bot.py
CMD ["python", "/bot.py"]