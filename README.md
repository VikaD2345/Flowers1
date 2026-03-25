# Flowers App

## Run

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

### URLs
- Site: `http://localhost:5173`
- Admin: `http://localhost:5173/admin`
- API: `http://127.0.0.1:8100`

## Admin

- Username: `admin`
- Password: value from `.env` in `ADMIN_PASSWORD`

The backend syncs the bootstrap admin on startup. After restarting the backend, the `admin` user's password is updated from `.env`.

## Ollama

### Installed paths
- Binary: `C:\Users\PC\AppData\Local\Programs\Ollama\ollama.exe`
- Models: `D:\всякое\ollama\models`

`C:\Users\PC\.ollama\models` is configured as a junction to `D:\всякое\ollama\models`, so model storage stays on `D:`.

### Start Ollama manually
```powershell
$env:OLLAMA_MODELS='D:\всякое\ollama\models'
& 'C:\Users\PC\AppData\Local\Programs\Ollama\ollama.exe' serve
```

### Check installed models
```powershell
$env:OLLAMA_MODELS='D:\всякое\ollama\models'
& 'C:\Users\PC\AppData\Local\Programs\Ollama\ollama.exe' list
```

### Quick model test
```powershell
$env:OLLAMA_MODELS='D:\всякое\ollama\models'
& 'C:\Users\PC\AppData\Local\Programs\Ollama\ollama.exe' run llama3 "Ответь одним словом: ok"
```

## Assistant

The assistant uses `llama3` through `Ollama`.

### Environment variables
In `.env`:
```env
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3
OLLAMA_TIMEOUT_SECONDS=45
```

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
  "base_url": "http://127.0.0.1:11434",
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

## Notes

- If PostgreSQL is reachable only through Radmin VPN, the assistant and admin data screens will not work until VPN is connected.
- `/assistant/health` checks Ollama only.
- `/assistant/chat` needs both Ollama and database access.
