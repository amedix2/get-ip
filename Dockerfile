FROM python:3.12-alpine
LABEL authors="amedix"
COPY requirements.txt .

RUN pip3 install --user --no-cache -r requirements.txt

COPY app/main.py .

ENTRYPOINT ["python3", "-u", "./main.py"]