FROM python:slim
RUN mkdir /app
WORKDIR /app
COPY ./requirements.txt /app/
RUN pip install -r requirements.txt
COPY ./db.py /app/
COPY ./app.py /app/app.py
CMD ["uvicorn", "app:app", "--host", "0.0.0.0"] 