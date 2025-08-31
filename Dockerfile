# === Builder stage ===
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

# Системные зависимости для сборки (если нужны для компиляции)
RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc python3-dev \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Устанавливаем зависимость torch ДО копирования pyproject.toml
RUN uv pip install --system --no-cache-dir torch --index-url \
    https://download.pytorch.org/whl/cpu

# Копируем файлы конфигурации uv и зависимости
COPY pyproject.toml uv.lock ./

# Устанавливаем зависимость torch и остальные
RUN uv pip install --system --no-cache-dir . \
 && apt-get purge -y gcc python3-dev \
 && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*

# === Runtime stage ===
FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Копируем зависимости из builder-стадии
COPY --from=builder /usr/local /usr/local

# Копируем код приложения
COPY . /app

# TODO: Создать пользователя и перключиься на него(права?)

CMD ["python", "main.py"]