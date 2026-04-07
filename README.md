# Flowers App

## Run

### Docker
```powershell
cd d:\flowers-app
docker compose up -d --build
docker compose run --rm --profile init ollama-pull
```

### Docker URLs
- Site: `http://localhost:5173`
- Admin: `http://localhost:5173/admin`
- API: `http://127.0.0.1:8100`
- Ollama API: `http://127.0.0.1:11434`
- pgAdmin: `http://localhost:5050`

### Backend
```powershell
cd d:\flowers-app\backend
.\venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8100
```

### Frontend
```powershell
cd d:\flowers-app\front
npm.cmd install
npm.cmd run dev
```

### Local URLs
- Site: `http://localhost:5173`
- Admin: `http://localhost:5173/admin`
- API: `http://127.0.0.1:8100`

## Admin

- Username: `admin`
- Password: value from `.env` in `ADMIN_PASSWORD`

The backend syncs the bootstrap admin on startup. After restarting the backend, the `admin` user's password is updated from `.env`.

## Ollama

### Docker service
```powershell
docker compose up -d ollama
```

### Pull model
```powershell
docker compose run --rm --profile init ollama-pull
```

### Check installed models
```powershell
docker exec -it flowers_ollama ollama list
```

### Quick model test
```powershell
docker exec -it flowers_ollama ollama run llama3.2 "Answer with one word: ok"
```

## Assistant

The assistant uses `llama3` through `Ollama`.

### Environment variables
In `.env`:
```env
OLLAMA_MODEL=llama3
OLLAMA_TIMEOUT_SECONDS=45
```

Inside Docker, backend uses `http://ollama:11434`.

### Health check
Check that backend can reach Ollama:
```powershell
curl http://127.0.0.1:8100/assistant/health
```

Expected response shape:
```json
{
  "status": "ok",
  "provider": "ollama",
  "model": "llama3",
  "base_url": "http://ollama:11434",
  "reply": "ok"
}
```

### Chat endpoint
```http
POST /assistant/chat
Content-Type: application/json
```

Example body:
```json
{
  "messages": [
    { "role": "user", "content": "Хочу что-то недорогое и нежное девушке" }
  ],
  "limit": 3
}
```

Behavior:
- extracts style, recipient and budget
- asks one short follow-up question if budget is missing
- searches real products in the database
- returns a reply based only on backend data

## Forecast

В backend добавлен модуль прогнозирования сезонного спроса на основе `XGBoost`.

### What XGBoost does

`XGBoost` анализирует историю ежедневных заказов, учитывает календарные признаки и строит прогноз будущего спроса.

В этом проекте модуль:
- загружает историю заказов из `synthetic_orders.csv`
- агрегирует данные по дням
- учитывает календарные сезонности и пиковые даты
- прогнозирует дневной спрос, начиная с текущей даты
- рассчитывает план закупок с запасом

План закупок считается по формуле:
- `purchase_plan = forecast * (1 + safety_stock)`

По умолчанию запас составляет `15%`.

### Data source

Синтетическая история заказов хранится в:
- `d:\flowers-app\synthetic_orders.csv`

Обязательные колонки:
- `order_id`
- `order_date`
- `quantity`
- `category`
- `status`

### Train model

```powershell
cd d:\flowers-app\backend
.\venv\Scripts\python.exe train_xgboost.py
```

Ожидаемый результат:
- модель сохраняется в `backend\xgboost_model.joblib`

### Run backend locally

```powershell
cd d:\flowers-app\backend
.\venv\Scripts\uvicorn.exe main:app --reload
```

Swagger:
- `http://127.0.0.1:8100/docs`

### Endpoints

#### Health

```powershell
Invoke-RestMethod http://127.0.0.1:8100/forecast/health
```

Ожидаемый ответ:

```json
{
  "model_loaded": true
}
```

#### Forecast

```powershell
Invoke-RestMethod "http://127.0.0.1:8100/forecast?days=5&safety_stock=0.15"
```

Пример ответа:

```json
[
  {
    "date": "2026-03-27",
    "forecast": 22,
    "purchase_plan": 25
  }
]
```

Параметры:
- `days` - количество дней прогноза, по умолчанию `30`
- `safety_stock` - коэффициент страхового запаса, по умолчанию `0.15`

#### Retrain

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8100/forecast/retrain
```

Этот endpoint переобучает модель по данным из `synthetic_orders.csv` и перезаписывает `backend\xgboost_model.joblib`.

### Docker

Если backend запускается через Docker, после изменений backend нужно пересобрать контейнер `app`:

```powershell
cd d:\flowers-app
docker compose up -d --build app
```

## Notes

- `/assistant/health` checks Ollama only.
- `/assistant/chat` needs both Ollama and database access.
