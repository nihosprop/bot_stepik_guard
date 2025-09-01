# === Builder stage ===
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

# Системные зависимости для сборки (если нужны для компиляции) и torch
RUN apt-get update \
  && apt-get install -y --no-install-recommends gcc python3-dev \
  && uv pip install --system --no-cache-dir torch --index-url \
                         https://download.pytorch.org/whl/cpu \
  && apt-get purge -y gcc python3-dev \
  && apt-get autoremove -y \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем файлы конфигурации uv и зависимости
COPY pyproject.toml uv.lock ./

# Установка остальных зависимостей
RUN uv pip install --system --no-cache-dir .

# === Runtime stage ===
FROM python:3.13-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Копируем зависимости из builder-стадии
COPY --from=builder /usr/local /usr/local

# Копируем код приложения
COPY . /app

# TODO: Создать пользователя и перключиься на него(права?)

CMD ["python", "main.py"]