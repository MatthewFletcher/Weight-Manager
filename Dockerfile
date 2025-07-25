FROM python:3.13-slim

WORKDIR /app
# Install git
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

VOLUME ["/app/data"]

EXPOSE 9600

