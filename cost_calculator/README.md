# Product Cost Calculator

## Web App

Install the web dependencies in the project virtual environment:

```powershell
.\cost_env\Scripts\python.exe -m pip install -r requirements.txt
```

Start the FastAPI server:

```powershell
.\cost_env\Scripts\python.exe -m uvicorn api:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/ to use the React frontend. The API endpoints are:

- `GET /api/health`
- `POST /api/costs/calculate`
- `POST /api/costs/save`
