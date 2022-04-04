FROM python:slim
COPY ./src/requirements.txt /requirements.txt
RUN pip install -r /requirements.txt
COPY ./src/ingestor.py /
CMD ["python", "/ingestor.py"]
