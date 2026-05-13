# AskDB — Ask your database in plain English

> Type a question. Get real results. No SQL knowledge needed.

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green?style=flat-square)
![Groq](https://img.shields.io/badge/AI-Groq-orange?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-purple?style=flat-square)

AskDB lets you query any MySQL, PostgreSQL, or SQLite database using plain English.
Powered by Groq AI — fast, free, and runs entirely on your machine.

---

## Features

- **Natural language to SQL** — just ask questions like a human
- **Auto chart suggestions** — bar, line, and pie charts generated automatically
- **Schema-aware** — reads your real tables and columns, never guesses
- **Read-only safety** — only SELECT queries run, all writes are blocked
- **Multi-database** — MySQL, PostgreSQL, SQLite
- **Hide sensitive tables** — exclude tables like passwords or audit logs
- **Free AI** — powered by Groq (no OpenAI billing)

---

## Demo

```
Question:  "Show me top 5 employees by salary"
Generated: SELECT name, salary FROM employees ORDER BY salary DESC LIMIT 5
Result:    Table + bar chart rendered instantly
```

---

## Requirements

- Python 3.11+
- A Groq API key — free at https://console.groq.com
- One of: MySQL, PostgreSQL, or SQLite database

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/codewithzubair07/AskDB.git
cd AskDB/nl-to-sql
```

### 2. Configure environment

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env`:

```dotenv
# Your database connection
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/dbname

# Groq AI (free at https://console.groq.com)
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# Optional
MAX_ROWS=200
EXCLUDED_TABLES=secrets,passwords,audit_logs
```

**DATABASE_URL examples:**

| Database   | Format |
|------------|--------|
| SQLite     | `sqlite:////absolute/path/to/file.db` |
| MySQL      | `mysql+pymysql://user:pass@localhost:3306/dbname` |
| PostgreSQL | `postgresql://user:pass@localhost:5432/dbname` |

### 3. Run

**Windows:**
```cmd
start.bat
```

**Linux / Mac:**
```bash
chmod +x start.sh && ./start.sh
```

### 4. Open

```
http://localhost:8000/app
```

---

## Project Structure

```
nl-to-sql/
├── backend/
│   ├── main.py              # FastAPI app and API routes
│   ├── query_engine.py      # Groq AI — natural language to SQL
│   ├── schema_inspector.py  # Reads your database schema
│   ├── db_connector.py      # Database connection
│   ├── security.py          # Blocks non-SELECT queries
│   ├── models.py            # Request/response models
│   └── requirements.txt
├── frontend/
│   └── index.html           # Web UI
├── .env.example
├── start.bat                # Windows launcher
└── start.sh                 # Linux/Mac launcher
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Server and DB status |
| GET | `/api/schema` | All tables and columns |
| GET | `/api/suggestions` | Auto-generated sample questions |
| POST | `/api/query` | Run a natural language query |

---

## Switch AI Model

Edit `GROQ_MODEL` in your `.env`:

| Model | Best for |
|-------|----------|
| `llama-3.3-70b-versatile` | Best quality (default) |
| `llama3-8b-8192` | Faster responses |
| `mixtral-8x7b-32768` | Good alternative |

---

## Security

- Only `SELECT` queries are allowed — all writes are blocked before execution
- Sensitive tables can be hidden via `EXCLUDED_TABLES` in `.env`
- Your data never leaves your machine — Groq only receives the question and schema

---

## Contributing

Pull requests are welcome. For major changes, open an issue first.

---

## License

MIT