FROM python:slim
RUN apt update && apt install -y git
RUN pip install git+https://github.com/JustinGuese/tradingbot-crypto-interactor
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY db.py /db.py
COPY app.py /app.py
CMD ["python", "/app.py"]