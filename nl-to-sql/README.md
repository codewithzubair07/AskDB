# AskDB — Ask your database in plain English

Ask questions like "show me top customers by revenue" 
and get real results from your real database instantly.
Runs 100% locally. Free. No cloud. No API keys.

## Requirements
- Python 3.11+
- Ollama → https://ollama.ai

## Setup

1. Install Ollama and pull a model:
   ollama pull llama3.2

2. Configure your database:
   cp backend/.env.example backend/.env
   Edit .env and set DATABASE_URL

3. Run:
   chmod +x start.sh && ./start.sh
   Open http://localhost:8000/app

## DATABASE_URL examples
SQLite:     sqlite:////path/to/file.db
PostgreSQL: postgresql://user:pass@localhost/mydb
MySQL:      mysql+pymysql://user:pass@localhost/mydb

## Hide sensitive tables
In .env: EXCLUDED_TABLES=passwords,tokens,audit_logs

## Switch AI model
In .env: OLLAMA_MODEL=codellama  (better SQL)
         OLLAMA_MODEL=mistral    (faster)
         OLLAMA_MODEL=llama3.2   (default)

## Security
- Read-only: only SELECT queries run
- All writes blocked before execution
- Data never leaves your machine
