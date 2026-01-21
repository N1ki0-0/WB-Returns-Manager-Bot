FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/
COPY requirements-dev.txt /app/

RUN pip install -U pip \
 && pip install -r requirements.txt \
 && pip install -r requirements-dev.txt

COPY . /app

CMD ["python", "-m", "app.presentation.telegram.bot"]