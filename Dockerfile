FROM python:slim

WORKDIR /app

COPY requirements.txt .
COPY metrics.py .
COPY Dockerfile .
COPY prometheus.yml .

RUN pip3 install --no-cache-dir -r requirements.txt
RUN python3 -m pip install psutil --find-links=https://ddelange.github.io/psutil/

EXPOSE 9000
