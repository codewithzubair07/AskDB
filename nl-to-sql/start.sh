#!/bin/bash
echo "Starting AskDB..."

# Check Ollama installed
if ! command -v ollama &> /dev/null; then
  echo "ERROR: Ollama not installed."
  echo "Install: https://ollama.ai"
  exit 1
fi

# Start Ollama if not running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
  echo "Starting Ollama..."
  ollama serve &
  sleep 3
fi

# Pull model
MODEL=$(grep OLLAMA_MODEL backend/.env | cut -d= -f2)
MODEL=${MODEL:-llama3.2}
echo "Pulling $MODEL..."
ollama pull $MODEL

# Check .env exists
if [ ! -f backend/.env ]; then
  echo "ERROR: backend/.env not found"
  echo "Run: cp backend/.env.example backend/.env"
  echo "Then set DATABASE_URL to your database"
  exit 1
fi

cd backend
pip install -r requirements.txt -q

echo ""
echo "=============================="
echo " AskDB running!"
echo " Open: http://localhost:8000/app"
echo "=============================="
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
