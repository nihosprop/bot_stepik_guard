# === Builder stage ===
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

# Системные зависимости для сборки (если нужны для компиляции)
RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc python3-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем файлы конфигурации uv и зависимости
COPY pyproject.toml uv.lock ./

# Устанавливаем зависимость torch и остальные
RUN uv pip install --system --no-cache-dir torch --index-url \
                https://download.pytorch.org/whl/cpu \
 && uv pip install --system .

# === Runtime stage ===
FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Копируем зависимости из builder-стадии
COPY --from=builder /usr/local/lib/python3.13/site-packages \
                    /usr/local/lib/python3.13/site-packages

# Копируем код приложения
COPY . /app

# TODO: Создать пользователя и перключиься на него(права?)

CMD ["python", "main.py"]