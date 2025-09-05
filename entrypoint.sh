#!/bin/sh
set -e

# Создаём каталоги, если их нет
mkdir -p /app/logs /app/.cache/huggingface

# Чиним владельца (appuser:appuser) рекурсивно
chown -R appuser:appuser /app/logs /app/.cache/huggingface

# Запускаем основную команду от appuser
exec gosu appuser "$@"
