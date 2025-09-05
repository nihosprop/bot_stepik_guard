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
COPY --from=builder /usr/local/lib/python3.13/site-packages \
                    /usr/local/lib/python3.13/site-packages

# Копируем код приложения
COPY . /app

RUN rm -rf $(which pip) $(which pip3) \
    /usr/local/bin/pip \
    /usr/local/bin/pip3 \
    /usr/local/bin/idle* \
    /usr/local/bin/pydoc* \
    /usr/local/bin/2to3* \
    /usr/local/bin/easy_install* \
    /usr/local/lib/python3.13/site-packages/pip* \
    /usr/local/lib/python3.13/site-packages/setuptools* \
    /usr/local/lib/python3.13/ensurepip	\
    /usr/share/doc \
    /usr/share/man \
    /usr/share/info	\
    /usr/share/lintian \
    /var/cache/apt/* \
    /var/cache/debconf/* \
    /var/cache/man/* \
    /var/lib/apt/lists/* \
 && find /usr/local/lib/python3.13/site-packages -type d -name '__pycache__' \
    -exec rm -rf {} + \
 && addgroup -S appuser \
 && adduser -S appuser -G appuser \
 && mkdir -p /app/logs \
 && chown -R appuser:appuser /app

USER appuser

CMD ["python", "main.py"]