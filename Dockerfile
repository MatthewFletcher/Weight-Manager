FROM python:3.12-slim

WORKDIR /app

# Install build tools if you need (for wheels, lxml, etc.)
RUN apt-get update && apt-get install -y git sqlite3 && rm -rf /var/lib/apt/lists/*

# Install Astral UV (latest)
RUN pip install --upgrade uv

COPY pyproject.toml ./
COPY requirements.txt ./
RUN uv pip install --system --upgrade .

COPY . .

EXPOSE 9600

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "9600"]
