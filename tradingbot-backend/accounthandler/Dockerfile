FROM python:slim
RUN mkdir -p /app/persistent
WORKDIR /app
COPY ./src/requirements.txt /app/
RUN pip install -r requirements.txt
COPY ./src/acchandler.py /app/
CMD ["python", "acchandler.py"]