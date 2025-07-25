FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

VOLUME ["/app/data"]

EXPOSE 9600

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "9600"]

