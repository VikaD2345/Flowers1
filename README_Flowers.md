# Flowers — интернет-магазин букетов

**Flowers** — учебный командный pet-проект веб-приложения для продажи букетов и управления заказами.  
Проект реализован как полноценное fullstack-приложение: пользовательская часть, личный кабинет, корзина, оформление заказов, административная панель, база данных, AI-ассистент и модуль прогнозирования спроса.

## Моя роль в проекте

В проекте я отвечал за **frontend-разработку**:

- верстка пользовательского интерфейса;
- создание страниц и компонентов приложения;
- разработка клиентской части на React;
- настройка маршрутизации между страницами;
- отображение каталога букетов и карточек товаров;
- реализация интерфейса корзины и оформления заказа;
- работа с авторизацией пользователя на frontend;
- подключение frontend к backend через REST API;
- отображение данных, полученных с сервера;
- участие в командной разработке и работе с Git.

## Основной функционал

### Пользовательская часть

- главная страница интернет-магазина;
- каталог букетов;
- разделение товаров по категориям;
- карточки товаров с названием, описанием и ценой;
- регистрация и авторизация пользователей;
- личный кабинет пользователя;
- корзина товаров;
- изменение количества товаров в корзине;
- удаление товаров из корзины;
- оформление заказа;
- просмотр истории заказов пользователя;
- блоки FAQ, преимуществ, галереи и контактов;
- AI-ассистент для помощи с подбором букета.

### Административная панель

В проекте есть отдельная админ-панель по адресу `/admin`.

Функции администратора:

- вход в административную панель;
- просмотр dashboard;
- управление товарами;
- добавление новых букетов;
- редактирование информации о товарах;
- удаление товаров;
- просмотр заказов;
- изменение статуса заказа;
- удаление заказов;
- просмотр пользователей;
- удаление пользователей;
- просмотр журнала действий администратора;
- просмотр прогноза спроса на букеты.

### Backend

Backend реализован на **FastAPI** и отвечает за:

- регистрацию и авторизацию пользователей;
- выдачу JWT-токенов;
- хранение пользователей, товаров, корзины и заказов;
- работу с PostgreSQL через SQLAlchemy;
- обработку запросов от frontend;
- административные операции;
- ведение audit log;
- работу AI-ассистента через Ollama;
- прогнозирование спроса на основе XGBoost.

### AI-ассистент

В проект добавлен ассистент, который помогает пользователю подобрать букет.  
Он анализирует сообщение пользователя, пытается определить бюджет, стиль, повод или получателя и предлагает подходящие товары из базы данных.

Ассистент работает через **Ollama** и локальную LLM-модель.

### Прогнозирование спроса

В backend есть модуль прогнозирования спроса на букеты.  
Он использует историю заказов из файла `synthetic_orders.csv` и модель **XGBoost**.

Модуль может:

- анализировать историю заказов;
- строить прогноз спроса на несколько дней вперед;
- рассчитывать план закупок с учетом страхового запаса;
- показывать метрики качества прогноза;
- переобучать модель.

## Технологии

### Frontend

- React
- React Router DOM
- Vite
- JavaScript
- HTML
- CSS

### Backend

- Python
- FastAPI
- Uvicorn
- SQLAlchemy
- Pydantic
- JWT
- Passlib

### Database

- PostgreSQL
- pgAdmin

### ML / AI

- Ollama
- Llama 3 / Llama 3.2
- XGBoost
- Pandas
- NumPy
- Scikit-learn
- Joblib

### DevOps / Tools

- Docker
- Docker Compose
- Git
- GitHub

## Структура проекта

```text
flowers-app/
├── backend/                    # Backend на FastAPI
│   ├── main.py                 # Основной файл API
│   ├── database.py             # Подключение к базе данных
│   ├── models.py               # SQLAlchemy-модели
│   ├── forecast.py             # API для прогноза спроса
│   ├── forecast_service.py     # Логика ML-прогнозирования
│   ├── ollama_assistant.py     # Логика AI-ассистента
│   ├── prompts.py              # Промпты для ассистента
│   ├── train_xgboost.py        # Скрипт обучения модели
│   ├── xgboost_model.joblib    # Сохраненная модель XGBoost
│   ├── requirements.txt        # Python-зависимости
│   └── Dockerfile              # Dockerfile для backend
│
├── front/                      # Frontend на React + Vite
│   ├── src/
│   │   ├── components/         # Компоненты пользовательской части
│   │   ├── admin/              # Компоненты и страницы админ-панели
│   │   ├── api/                # Запросы к backend API
│   │   ├── utils/              # Вспомогательные функции
│   │   ├── assets/             # Изображения и иконки
│   │   ├── fonts/              # Шрифты
│   │   ├── App.jsx             # Главный компонент приложения
│   │   ├── PublicApp.jsx       # Пользовательская часть сайта
│   │   └── main.jsx            # Точка входа frontend
│   ├── package.json            # Зависимости frontend
│   ├── vite.config.js          # Настройки Vite
│   └── Dockerfile              # Dockerfile для frontend
│
├── docker-compose.yml          # Запуск проекта через Docker Compose
├── synthetic_orders.csv        # Данные для ML-прогнозирования
├── init.sql                    # SQL-структура базы данных
├── dump.sql                    # Дамп базы данных
├── .env.example                # Пример переменных окружения
└── README.md                   # Описание проекта
```

## Запуск проекта через Docker

Это основной и самый удобный способ запуска, потому что через Docker поднимаются сразу:

- frontend;
- backend;
- PostgreSQL;
- pgAdmin;
- Ollama.

### 1. Клонировать репозиторий

```bash
git clone https://github.com/USERNAME/REPOSITORY_NAME.git
cd REPOSITORY_NAME
```

Вместо `USERNAME` и `REPOSITORY_NAME` нужно указать свои данные GitHub-репозитория.

### 2. Создать файл `.env`

Создайте файл `.env` в корне проекта на основе `.env.example`.

Для macOS / Linux:

```bash
cp .env.example .env
```

Для Windows PowerShell:

```powershell
copy .env.example .env
```

Пример содержимого `.env`:

```env
POSTGRES_DB=flowers_db
POSTGRES_USER=flowers_user
POSTGRES_PASSWORD=flowers_pass

DATABASE_URL=postgresql+psycopg2://flowers_user:flowers_pass@db:5432/flowers_db

JWT_SECRET=change_this_secret_key
JWT_ALG=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

ADMIN_USERNAME=admin
ADMIN_PASSWORD=1qaz

OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama3.2:1b
OLLAMA_REPLY_MODEL=llama3.2:1b
OLLAMA_EXTRACTION_MODEL=llama3.2:1b
OLLAMA_EXTRACT_WITH_LLM=false
OLLAMA_TIMEOUT_SECONDS=45

PGADMIN_DEFAULT_EMAIL=admin@flowers.com
PGADMIN_DEFAULT_PASSWORD=admin123
```

> Важно: настоящий файл `.env` не нужно загружать на GitHub, потому что в нем могут быть пароли и секретные ключи.

### 3. Запустить контейнеры

```bash
docker compose up -d --build
```

### 4. Загрузить модель для Ollama

```bash
docker compose run --rm --profile init ollama-pull
```

По умолчанию используется модель из переменной `OLLAMA_MODEL`, например:

```env
OLLAMA_MODEL=llama3.2:1b
```

### 5. Открыть приложение

После запуска будут доступны адреса:

| Сервис | Адрес |
|---|---|
| Сайт | `http://localhost:5173` |
| Админ-панель | `http://localhost:5173/admin` |
| Backend API | `http://127.0.0.1:8100` |
| Swagger / API docs | `http://127.0.0.1:8100/docs` |
| Ollama API | `http://127.0.0.1:11434` |
| pgAdmin | `http://localhost:5050` |

## Данные для входа в админ-панель

Админ создается автоматически при старте backend.

По умолчанию:

```text
Логин: admin
Пароль: 1qaz
```

Если вы измените `ADMIN_USERNAME` или `ADMIN_PASSWORD` в `.env`, после перезапуска backend данные администратора обновятся.

## Запуск без Docker

Можно запустить frontend и backend отдельно. Этот вариант удобен для разработки.

### 1. Запустить PostgreSQL

Можно поднять только базу данных через Docker:

```bash
docker compose up -d db
```

В этом случае база будет доступна на порту `5433`.

Для локального запуска backend в `.env` лучше использовать такую строку подключения:

```env
DATABASE_URL=postgresql+psycopg2://flowers_user:flowers_pass@127.0.0.1:5433/flowers_db
```

### 2. Запустить backend

Перейдите в папку backend:

```bash
cd backend
```

Создайте виртуальное окружение:

```bash
python -m venv venv
```

Активируйте окружение.

Для macOS / Linux:

```bash
source venv/bin/activate
```

Для Windows PowerShell:

```powershell
.\venv\Scripts\activate
```

Установите зависимости:

```bash
pip install -r requirements.txt
```

Запустите backend:

```bash
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8100
```

Backend будет доступен по адресу:

```text
http://127.0.0.1:8100
```

Swagger-документация:

```text
http://127.0.0.1:8100/docs
```

### 3. Запустить frontend

В новом терминале перейдите в папку frontend:

```bash
cd front
```

Установите зависимости:

```bash
npm install
```

Запустите frontend:

```bash
npm run dev
```

Frontend будет доступен по адресу:

```text
http://localhost:5173
```

## Основные API endpoints

### Проверка backend

```http
GET /health
```

### Авторизация

```http
POST /auth/register
POST /auth/login
GET /me
```

### Каталог товаров

```http
GET /flowers
GET /flowers/{flower_id}
```

### Корзина

```http
GET /cart
POST /cart/items
PATCH /cart/items/{item_id}
DELETE /cart/items/{item_id}
```

### Заказы

```http
POST /orders/from-cart
GET /me/orders
GET /orders/{order_id}
```

### Админ-панель

```http
GET /admin/orders
PATCH /admin/orders/{order_id}/status
DELETE /admin/orders/{order_id}

GET /admin/users
DELETE /admin/users/{user_id}

POST /admin/flowers
PATCH /admin/flowers/{flower_id}
DELETE /admin/flowers/{flower_id}

GET /admin/audit
```

### AI-ассистент

```http
GET /assistant/health
POST /assistant/chat
POST /assistant/chat/stream
```

Пример запроса:

```json
{
  "messages": [
    {
      "role": "user",
      "content": "Хочу недорогой нежный букет девушке"
    }
  ],
  "limit": 3
}
```

### Прогноз спроса

```http
GET /forecast/health
GET /forecast?days=30&safety_stock=0.15
GET /forecast/metrics?test_days=30
POST /forecast/retrain
```

Пример запроса прогноза:

```bash
curl "http://127.0.0.1:8100/forecast?days=7&safety_stock=0.15"
```

## Работа с базой данных

Проект использует PostgreSQL.

Основные таблицы:

- `app_users` — пользователи;
- `bouquets` — букеты;
- `app_cart_items` — товары в корзине;
- `app_orders` — заказы;
- `app_order_items` — состав заказа;
- `audit_logs` — журнал действий администратора.

При запуске backend таблицы создаются автоматически через SQLAlchemy.

## Проверка работы проекта

После запуска проекта можно проверить:

1. Открыть главную страницу: `http://localhost:5173`.
2. Перейти в каталог.
3. Зарегистрировать нового пользователя.
4. Войти в аккаунт.
5. Добавить букет в корзину.
6. Изменить количество товара в корзине.
7. Оформить заказ.
8. Перейти в личный кабинет и проверить историю заказов.
9. Открыть админ-панель: `http://localhost:5173/admin`.
10. Войти под администратором.
11. Проверить список заказов, товаров и пользователей.
12. Изменить статус заказа.
13. Проверить прогноз спроса.
14. Проверить AI-ассистента на главной странице.

## Команды Docker

Запустить проект:

```bash
docker compose up -d --build
```

Остановить проект:

```bash
docker compose down
```

Остановить проект и удалить volumes с данными:

```bash
docker compose down -v
```

Посмотреть запущенные контейнеры:

```bash
docker ps
```

Посмотреть логи backend:

```bash
docker logs flowers_app
```

Посмотреть логи frontend:

```bash
docker logs flowers_front
```

Посмотреть установленные модели Ollama:

```bash
docker exec -it flowers_ollama ollama list
```

Проверить модель Ollama:

```bash
docker exec -it flowers_ollama ollama run llama3.2:1b "Answer with one word: ok"
```

## Возможные проблемы

### Порт уже занят

Если появляется ошибка, что порт уже используется, проверьте занятые порты:

```bash
lsof -i :5173
lsof -i :8100
lsof -i :5433
```

На Windows можно использовать:

```powershell
netstat -ano | findstr :5173
netstat -ano | findstr :8100
netstat -ano | findstr :5433
```

### Frontend не видит backend

Проверьте, что backend запущен и доступен:

```text
http://127.0.0.1:8100/health
```

Также проверьте переменную окружения для frontend:

```env
VITE_API_URL=http://127.0.0.1:8100
```

### AI-ассистент не отвечает

Проверьте, что Ollama запущена:

```bash
docker ps
```

Проверьте health endpoint:

```text
http://127.0.0.1:8100/assistant/health
```

Проверьте, что модель загружена:

```bash
docker exec -it flowers_ollama ollama list
```

### Не получается войти в админ-панель

Проверьте переменные в `.env`:

```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD=1qaz
```

После изменения `.env` перезапустите backend:

```bash
docker compose restart app
```

## Что не стоит загружать на GitHub

В репозиторий не нужно добавлять:

- `.env`;
- `node_modules/`;
- `dist/`;
- `.vite/`;
- `__pycache__/`;
- `.DS_Store`;
- папку `__MACOSX/`;
- временные файлы IDE.

Для этого лучше добавить в `.gitignore`:

```gitignore
.env
.env.*
!.env.example

node_modules/
dist/
.vite/
__pycache__/
*.pyc
.DS_Store
__MACOSX/
.vscode/
.idea/
```

## Статус проекта

Проект выполнен в учебных целях и может использоваться как pet-проект в портфолио frontend-разработчика.

## Авторство

Проект разрабатывался в команде.  
Моя зона ответственности — frontend-часть приложения: интерфейс, страницы, компоненты, клиентская логика и интеграция с backend API.
