# BotStepikGuard 🛡️

[![Version](https://img.shields.io/badge/version-v1.0-blue)](https://github.com/yourname/BotStepikGuard/releases)
[![Python](https://img.shields.io/badge/Python-3.13.1-green)](https://www.python.org/)
[![Aiogram](https://img.shields.io/badge/Aiogram-3.21-brightgreen)](https://docs.aiogram.dev/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Redis](https://img.shields.io/badge/Redis-7-red)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-20.10%2B-blue)](https://www.docker.com/)

**Умный страж комментариев** для платформы Stepik, автоматически выявляющий нежелательный контент и нарушения.

## 🔍 Возможности

- **Мониторинг в реальном времени** новых комментариев на курсах Stepik
- **Продвинутая фильтрация** с использованием:
  - Регулярных выражений
  - Алгоритма Левенштейна
- **Гибкая система уведомлений** в Telegram:
  - Мгновенные алерты

## 🛠 Технологический стек

| Компонент          | Назначение                                                                      |
|--------------------|---------------------------------------------------------------------------------|
| **Python 3.13+**   | Основной язык разработки                                                        |
| **Aiogram**        | Telegram Bot Framework                                                          |
| **Redis**          | Кеширование и временные данные                                                  |
| **Docker**         | Контейнеризация                                                                 |
| **docker-compose** | Деплой                                                                          |
| **Stepik API**     | Интеграция с образовательной платформой                                         |
| **GitHub Actions** | После каждого пуша авто-сборка образа и отправка его в репозиторий на DockerHub |

## 🚀 Быстрый старт

```bash

# Клонирование репозитория
git clone https://github.com/nihosprop/bot_stepik_guard.git
```

### Структура на сервере
```
your_name_bot_dir
├── docker-compose.yml
├── .env
└── redis
    └── redis.conf

1. Прописать docker-compose.yml по аналогии docker-composePROD.yml,
заменив данные на свои.

2. Прописать .env по аналогии .env.PROD, заменив данные на свои

2. Прописать redis.conf под свои нужды..

! Задать пароль для Redis в .env и redis.conf
! Redis пароли должны совпадать в .env и redis.conf
```
### Деплой через docker-composePROD

```code
# Находясь в корне проекта(бота) исполнить:

docker compose up -d
```

### 📅 Планируемые функции
- **Улучшенная аналитика**:
  - Отслеживание подозрительной динамики и действий
- **Расширенная модерация**:
  - Автоматические шаблоны ответов
  - Разные уровни уведомлений

### 💡 Долгосрочные цели
```mermaid
    A[Текущая версия] --> B(ML-фильтры)
    B --> C[Автомодерация]
```