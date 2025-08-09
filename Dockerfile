# Stage 1: Сборка зависимостей
FROM python:3.13.1-slim-bookworm AS builder

WORKDIR /install
COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

# Stage 2: Финальный образ
FROM python:3.13.1-slim-bookworm

WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .

CMD ["python", "main.py"]