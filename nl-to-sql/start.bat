@echo off
echo Starting AskDB...
cd backend
pip install -r requirements.txt -q
echo Open: http://localhost:8000/app
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
