# Мультиагентный аналитический ассистент Olist

Проект анализирует данные бразильского маркетплейса Olist на естественном
языке. Пользователь задаёт бизнес-вопрос, LangChain Orchestrator делегирует
подзадачи специализированным агентам, они вызывают подходящие MCP-инструменты,
а Critic формирует итоговый ответ только на основании собранных Evidence.

## Что умеет система

- анализировать продажи, заказы, выручку и средний чек;
- сравнивать продавцов и находить лидеров по показателям;
- анализировать ассортимент продавца и товарные категории;
- исследовать сроки доставки, задержки и регионы;
- анализировать рейтинги, негативные отзывы и клиентский опыт;
- проверять связь задержек доставки с оценками покупателей;
- показывать выполненные шаги, Evidence, факты, гипотезы и уверенность;
- сохранять полную трассировку LLM- и MCP-вызовов в Langfuse;
- проверять качество ответов на контрольном наборе через DeepEval.

## Архитектура

```text
Пользователь
    ↓
HTTP API / веб-интерфейс
    ↓
InvestigateQuestion
    ↓
LangChain Orchestrator
    ├── ask_sales_agent ───→ Sales Agent
    ├── ask_seller_agent ──→ Seller Agent
    ├── ask_delivery_agent → Delivery Agent
    └── ask_reviews_agent ─→ Reviews Agent
                              ↓
                      LangChain MCP adapter
                              ↓
                       FastMCP-инструменты
                              ↓
                           Use Cases
                              ↓
                    PostgreSQL repositories
                              ↓
                         PostgreSQL
                              ↓
                           Evidence
                              ↓
                    Critic / Evidence Agent
                              ↓
              факты, гипотезы и итоговый ответ
```

Проект разделён на слои:

- `domain/` — бизнес-сущности и интерфейсы репозиториев;
- `application/` — сценарии использования;
- `infrastructure/postgres/` — SQL и реализации репозиториев;
- `infrastructure/mcp/` — MCP-инструменты;
- `infrastructure/agents/` — оркестратор и специализированные агенты;
- `infrastructure/llm/` — создание OpenAI-совместимой модели LangChain;
- `infrastructure/observability/` — интеграция Langfuse и метрики времени;
- `interfaces/api/` — HTTP API;
- `interfaces/web/` — веб-интерфейс;
- `evaluation/` — контрольные кейсы, метрики и отчёты.

## Требования

- Python 3.11 или новее;
- PostgreSQL;
- CSV-файлы датасета Olist;
- доступ к LLM с OpenAI-совместимым Chat Completions API.

Для самого простого запуска достаточно установить Docker Desktop. Отдельно
устанавливать Python и PostgreSQL в этом случае не требуется.

## Простой запуск через Docker

Docker самостоятельно
создаст изолированное окружение для приложения и базы данных.

### 1. Установить и запустить Docker Desktop

Скачайте Docker Desktop для своей операционной системы, установите его и
дождитесь полного запуска. Затем откройте терминал в корневой папке проекта —
там, где находятся `compose.yaml` и `Dockerfile`.

Проверить, что Docker доступен:

```powershell
docker --version
docker compose version
```

Обе команды должны показать номер версии без ошибки.

### 2. Подготовить настройки

В корне проекта должен находиться файл `.env`. Его можно создать из безопасного
примера:

```powershell
Copy-Item .env.example .env
```

Откройте `.env` и заполните настройки базы и языковой модели:

```dotenv
DB_HOST=localhost
DB_PORT=5432
DB_NAME=olist
DB_USER=postgres
DB_PASSWORD=your_password

LLM_BASE_URL=https://your-provider.example/v1
LLM_API_KEY=your_api_key
LLM_MODEL=your_model_name
```

При запуске через Docker значения `DB_HOST` и `DB_PORT` для контейнеров будут
автоматически заменены на `db` и `5432`. Поэтому приведённые выше значения
можно оставить без изменений.

Настоящий API-ключ нельзя публиковать в GitHub или передавать вместе с
проектом.

### 3. Добавить данные Olist

https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

Поместите девять CSV-файлов датасета в папку `data/raw/`. Список необходимых
файлов приведён ниже в разделе «Загрузка данных». Сами CSV не входят в
Docker-образ и подключаются к загрузчику как внешняя папка.

### 4. Запустить PostgreSQL

```powershell
docker compose up -d db
```

Docker скачает официальный образ PostgreSQL, создаст контейнер базы и запустит
его в фоне. При первом запуске скачивание может занять несколько минут.

Проверить состояние контейнера:

```powershell
docker compose ps
```

У сервиса `db` через некоторое время должно появиться состояние `healthy`.

### 5. Загрузить CSV в базу

```powershell
docker compose run --rm --build loader
```

Команда собирает образ проекта, создаёт временный контейнер `loader`, загружает
CSV в PostgreSQL и удаляет этот временный контейнер после завершения. В конце
должно появиться сообщение `Все данные загружены!`.

Загрузчик нужно выполнять при первом запуске и после замены CSV. При повторном
запуске соответствующие таблицы будут созданы заново из текущих файлов.

### 6. Запустить приложение

```powershell
docker compose up -d --build app
```

После запуска откройте в браузере:

```text
http://127.0.0.1:8000
```

Если страница не открывается, посмотрите состояние и журнал приложения:

```powershell
docker compose ps
docker compose logs --tail=100 app
```

Адрес `0.0.0.0:8000` в журнале означает, что сервер слушает подключения внутри
контейнера. В браузере всё равно следует открывать `127.0.0.1:8000` или
`localhost:8000`.

### Последующие запуски

Если образы уже собраны, а данные загружены, достаточно выполнить:

```powershell
docker compose up -d db app
```

После изменения Python, HTML, CSS или JavaScript пересоберите только
приложение:

```powershell
docker compose up -d --build app
```

После изменения только `.env` пересоздайте контейнер приложения:

```powershell
docker compose up -d --force-recreate app
```

### Остановка

Безопасно остановить проект, сохранив загруженную базу:

```powershell
docker compose down
```

Данные PostgreSQL находятся в Docker volume `postgres_data` и после обычной
остановки сохраняются. Команда `docker compose down -v` дополнительно удаляет
volume и всю загруженную базу, поэтому использовать её следует только для
полного сброса проекта.

### Что запускает Docker Compose

| Сервис | Назначение | Когда нужен |
|---|---|---|
| `db` | PostgreSQL с данными Olist | Работает вместе с приложением |
| `loader` | Загружает CSV в PostgreSQL | Первый запуск или обновление данных |
| `app` | API, агенты и веб-интерфейс | Основная работа пользователя |

## Локальный запуск без Docker

Следующие разделы нужны только в том случае, если проект запускается напрямую
через установленный Python и локальный PostgreSQL.

## Подготовка проекта

Создайте и активируйте виртуальное окружение из корня проекта:

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
```

Установите Python-зависимости в активированное окружение:

```powershell
pip install -r requirements.txt
```

Создайте локальный `.env` из безопасного шаблона:

```powershell
Copy-Item .env.example .env
```

Создайте базу данных PostgreSQL, затем укажите в `.env` параметры подключения
и LLM:

```dotenv
DB_HOST=localhost
DB_PORT=5432
DB_NAME=olist
DB_USER=postgres
DB_PASSWORD=your_password

LLM_BASE_URL=https://your-provider.example/v1
LLM_API_KEY=your_api_key
LLM_MODEL=your_model_name
```

Не добавляйте настоящий `.env` и API-ключи в Git.

## Загрузка данных

Положите исходные CSV-файлы в `data/raw/`:

```text
olist_customers_dataset.csv
olist_orders_dataset.csv
olist_order_items_dataset.csv
olist_products_dataset.csv
olist_sellers_dataset.csv
olist_order_payments_dataset.csv
olist_order_reviews_dataset.csv
olist_geolocation_dataset.csv
product_category_name_translation.csv
```

Запустите загрузку из корня проекта:

```powershell
py -m scripts.load_data
```

Скрипт создаст в указанной базе схему `raw` и загрузит девять таблиц. Таблицы
создаются в PostgreSQL, а не в папке проекта.

## Запуск веб-интерфейса

Из корня проекта выполните:

```powershell
py -m uvicorn interfaces.api.app:app --host 127.0.0.1 --port 8000
```

После запуска откройте в браузере:

```text
http://127.0.0.1:8000
```

Если порт занят или Windows запрещает доступ к нему, выберите другой:

```powershell
py -m uvicorn interfaces.api.app:app --host 127.0.0.1 --port 8010
```

API принимает запрос:

```http
POST /api/investigations
Content-Type: application/json
```

```json
{
  "question": "Почему у продавца X рейтинг ниже среднего?"
}
```

## Запуск из консоли

Консольный запуск исследования:

```powershell
py -m scripts.run_investigation
```

Он выводит результаты шагов, Evidence, факты, гипотезы и итоговый ответ.

## Evaluation

Контрольный набор содержит 25 бизнес-кейсов:

- 16 детерминированных кейсов с ожидаемыми инструментами и фактами;
- 9 исследовательских кейсов с проверкой полноты, Evidence и гипотез.

Все проверки выполняются через DeepEval. Он оценивает выбор инструментов,
релевантность ответа, соответствие Evidence, бизнес-корректность и качество
исследовательского анализа.

Запустить один кейс:

```powershell
deepeval test run evaluation/deepeval_suite/test_agents.py -k D001
```

Запустить только исследовательские кейсы:

```powershell
deepeval test run evaluation/deepeval_suite/test_agents.py -m research
```

Запустить весь набор с автоматической записью структурированного отчёта:

```powershell
python -m evaluation.run_deepeval
```

Подробная инструкция находится в [`evaluation/README.md`](evaluation/README.md),
а описание метрик — в [`evaluation/METRICS.md`](evaluation/METRICS.md).
Актуальные отчёты сохраняются в `evaluation/reports/deepeval_results.json`
и `evaluation/reports/deepeval_results.md`.

## Основные технологии

- **LangChain** — агентные циклы, инструменты, сообщения и структурированный ответ;
- **FastMCP** — контролируемые инструменты доступа к бизнес-операциям;
- **LangChain MCP Adapters** — преобразование MCP-инструментов в LangChain Tools;
- **Langfuse** — трассировка полного пути запроса;
- **DeepEval** — автоматическая оценка ответов на контрольном наборе;
- **PostgreSQL** — хранение и аналитическая обработка данных Olist.

## Известные ограничения

- история диалога хранится только до обновления или закрытия страницы;
- работа агентов зависит от доступности внешней LLM и необходимого VPN;
- датасет является историческим и не показывает текущее состояние магазина;
- отзыв относится ко всему заказу и не всегда однозначно к одному продавцу;
- в исходных данных нет полной информации о возвратах, прибыли и себестоимости.

## Пример сложного исследования

Для вопроса «Почему у продавца X низкий рейтинг?» система может:

1. получить продажи и структуру заказов продавца;
2. сравнить его показатели со средними значениями;
3. проверить сроки доставки и долю задержек;
4. получить распределение и примеры негативных отзывов;
5. проверить связь задержек с низкими оценками;
6. сформировать вывод с привязкой к Evidence.
