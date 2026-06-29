# 🤖 WebMind — AI Web Scraper & RAG Chatbot

<div align="center">

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?logo=fastapi)
![LangChain](https://img.shields.io/badge/LangChain-0.3-orange)
![Qdrant](https://img.shields.io/badge/Qdrant-1.13-red)
![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-purple)
![Docker](https://img.shields.io/badge/Docker-Compose-blue?logo=docker)
![License](https://img.shields.io/badge/License-MIT-yellow)

**A fully local, production-ready RAG chatbot that scrapes any website and lets you chat with its content — zero cloud LLM costs.**

[Features](#-features) • [Architecture](#-architecture) • [Quick Start](#-quick-start) • [API Docs](#-api-reference) • [Deployment](#-deployment)

</div>

---

## 📌 Overview

WebMind is a **Retrieval-Augmented Generation (RAG)** system that:

1. **Scrapes** any website using Playwright (handles JavaScript-rendered pages)
2. **Indexes** content into Qdrant vector database with semantic embeddings
3. **Answers** questions about that content using a locally-running LLM via Ollama

Everything runs **100% locally** — no OpenAI API key, no cloud costs, no data leaving your machine.

---

## ✨ Features

- 🕷️ **Smart Web Scraping** — Playwright-based crawler handles dynamic JS sites, sitemap detection, and multi-page crawling
- 🧠 **Local LLM** — Powered by Ollama (llama3.2, mistral, or any supported model)
- 📦 **Vector Search** — Qdrant for fast semantic retrieval
- ⚡ **Redis Caching** — Query results cached to reduce redundant LLM calls
- 🗄️ **MySQL Persistence** — Index metadata and session history stored in MySQL
- 🔁 **Async Architecture** — FastAPI + asyncio for non-blocking I/O
- 🐳 **Fully Dockerized** — One command to run the entire stack
- 🔒 **Non-root Container** — Security-hardened Docker image

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Client / UI                          │
│                  (Browser / API Consumer)                   │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                          │
│                   (Port 8000)                               │
│                                                             │
│  POST /index     →  Scrape & Index Website                 │
│  GET  /index/:id →  Check Indexing Status                  │
│  POST /chat      →  RAG Query                              │
│  GET  /health    →  Health Check                           │
└────┬──────────────┬──────────────┬──────────────┬──────────┘
     │              │              │              │
     ▼              ▼              ▼              ▼
┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐
│Playwright│  │  Qdrant  │  │  Redis   │  │    MySQL     │
│Scraper  │  │Vector DB │  │  Cache   │  │  Metadata    │
│         │  │Port 6333 │  │Port 6379 │  │  Port 3306   │
└────┬────┘  └──────────┘  └──────────┘  └──────────────┘
     │
     ▼
┌─────────┐
│ Ollama  │
│Local LLM│
│Port 11434│
└─────────┘
```

### RAG Pipeline

```
User Query
    │
    ▼
Redis Cache Check ──── HIT ──→ Return Cached Response
    │
   MISS
    │
    ▼
Embed Query (Ollama Embeddings)
    │
    ▼
Qdrant Vector Search (Top-K chunks)
    │
    ▼
Context Assembly + Prompt Construction
    │
    ▼
Ollama LLM (Local Inference)
    │
    ▼
Response → Cache in Redis → Return to User
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **API Framework** | FastAPI 0.115 |
| **Web Scraping** | Playwright 1.52 + BeautifulSoup4 |
| **LLM Orchestration** | LangChain 0.3, LangChain-Ollama |
| **Vector Database** | Qdrant 1.13.6 |
| **Local LLM** | Ollama (llama3.2:3b default) |
| **Cache** | Redis 7 |
| **Relational DB** | MySQL 8.4 |
| **Validation** | Pydantic v2 |
| **Containerization** | Docker + Docker Compose |

---

## 📋 Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- [Ollama](https://ollama.com/) installed on your host machine
- Minimum **8GB RAM** recommended (4GB for Ollama + stack overhead)
- Git

---

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/madan-genai/Website-ChatBot.git
cd Website-ChatBot
```

### 2. Pull Required Ollama Models

Ollama must be running on your host machine **before** starting the stack.

```bash
# Start Ollama (if not already running)
ollama serve

# Pull the LLM (in a separate terminal)
ollama pull llama3.2:3b

# Pull the embedding model
ollama pull nomic-embed-text
```

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
# MySQL
MYSQL_PASSWORD=your_secure_password
MYSQL_DATABASE=webmind_db
MYSQL_HOST=mysql
MYSQL_PORT=3306

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Qdrant
QDRANT_HOST=qdrant
QDRANT_PORT=6333

# Ollama (host.docker.internal points to your host machine)
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.2:3b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# App
APP_ENV=production
LOG_LEVEL=INFO
```

### 4. Start the Stack

```bash
docker compose up -d
```

First run will pull all images (~3-4 GB). Subsequent starts take ~30 seconds.

### 5. Verify Everything is Running

```bash
docker compose ps
```

All services should show `healthy` or `running`:

```
NAME            STATUS          PORTS
rag-chatbot     running         0.0.0.0:8000->8000/tcp
mysql           healthy         3306/tcp
redis           healthy         0.0.0.0:6379->6379/tcp
qdrant          running         0.0.0.0:6333->6333/tcp
```

### 6. Open API Docs

```
http://localhost:8000/docs
```

---

## 📡 API Reference

### Health Check

```http
GET /health
```

```json
{
  "status": "healthy",
  "qdrant": "connected",
  "redis": "connected",
  "mysql": "connected"
}
```

---

### Index a Website

```http
POST /index
Content-Type: application/json

{
  "url": "https://example.com"
}
```

**Response:**

```json
{
  "index_id": "0e96b16f-e628-4ada-a3db-0bce685342dd",
  "status": "indexing",
  "url": "https://example.com"
}
```

Indexing runs asynchronously. Poll the status endpoint.

---

### Check Indexing Status

```http
GET /index/{index_id}
```

```json
{
  "index_id": "0e96b16f-e628-4ada-a3db-0bce685342dd",
  "status": "completed",
  "url": "https://example.com",
  "pages_indexed": 42,
  "chunks_stored": 318
}
```

**Status values:** `indexing` → `completed` | `failed`

---

### Chat with Indexed Website

```http
POST /chat
Content-Type: application/json

{
  "index_id": "0e96b16f-e628-4ada-a3db-0bce685342dd",
  "question": "What services does this company offer?"
}
```

**Response:**

```json
{
  "answer": "Based on the website content, the company offers...",
  "sources": [
    "https://example.com/services",
    "https://example.com/about"
  ],
  "cached": false
}
```

---

## 🗂️ Project Structure

```
Website-ChatBot/
├── app.py                  # FastAPI application, routes, lifecycle
├── scrape2.py              # Playwright web crawler
├── cache.py                # Redis cache layer
├── requirements.txt        # Python dependencies
├── Dockerfile              # Multi-stage, non-root Docker image
├── docker-compose.yml      # Full stack orchestration
├── .env.example            # Environment variable template
├── .dockerignore           # Docker build exclusions
├── data/                   # Persistent local data (gitignored)
└── README.md
```

---

## 🐳 Docker Details

### Services

| Service | Image | Port | Purpose |
|---|---|---|---|
| `rag-chatbot` | Custom build | 8000 | FastAPI application |
| `mysql` | mysql:8.4 | 3306 (internal) | Metadata storage |
| `redis` | redis:7-alpine | 6379 | Query cache |
| `qdrant` | qdrant/qdrant:v1.13.6 | 6333, 6334 | Vector database |

### Useful Commands

```bash
# Start in background
docker compose up -d

# View logs (all services)
docker compose logs -f

# View logs (specific service)
docker compose logs -f rag-chatbot

# Restart a service
docker compose restart rag-chatbot

# Stop everything
docker compose down

# Stop and delete all data (full reset)
docker compose down -v

# Rebuild after code changes
docker compose build --no-cache
docker compose up -d
```

---

## ☁️ Deployment

### Option 1: Oracle Cloud Always Free (Recommended — Zero Cost)

Oracle's Always Free tier includes a permanent ARM VM with **24GB RAM** — enough to run the full stack including Ollama.

```bash
# On Oracle ARM VM (Ubuntu)
# 1. Install Docker
curl -fsSL https://get.docker.com | sh

# 2. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:3b
ollama pull nomic-embed-text

# 3. Clone and run
git clone https://github.com/madan-genai/Website-ChatBot.git
cd Website-ChatBot
cp .env.example .env
# Edit .env — set OLLAMA_BASE_URL=http://localhost:11434
docker compose up -d
```

### Option 2: Cloudflare Tunnel (Free HTTPS — No Nginx Needed)

```bash
# Install cloudflared on your VM
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
dpkg -i cloudflared-linux-amd64.deb

# Authenticate and create tunnel
cloudflared tunnel login
cloudflared tunnel create webmind

# Route to FastAPI
cloudflared tunnel --url http://localhost:8000
```

Your app is now live at `https://webmind.yourdomain.com` with automatic HTTPS.

### Option 3: Hetzner VPS (Best Paid Value — ~$10/month)

```bash
# Hetzner CX32 (8GB RAM, 4 vCPU) — enough for full stack
# Same setup as Oracle above
```

### Option 4: Docker Hub

```bash
# Push your image
docker login
docker tag aiwebscraper-app:latest yourusername/webmind-rag:latest
docker push yourusername/webmind-rag:latest

# Pull and run on any server
docker pull yourusername/webmind-rag:latest
docker compose up -d
```

---

## ⚙️ Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `MYSQL_PASSWORD` | — | MySQL root password (required) |
| `MYSQL_DATABASE` | `webmind_db` | Database name |
| `MYSQL_HOST` | `mysql` | MySQL host (Docker service name) |
| `REDIS_HOST` | `redis` | Redis host |
| `QDRANT_HOST` | `qdrant` | Qdrant host |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Ollama endpoint |
| `OLLAMA_MODEL` | `llama3.2:3b` | LLM model name |
| `OLLAMA_EMBEDDING_MODEL` | `nomic-embed-text` | Embedding model |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

---

## 🔧 Troubleshooting

### MySQL container unhealthy

```bash
docker compose logs mysql
# If "can't connect" → increase start_period in healthcheck
# If "access denied" → docker compose down -v and restart (stale volume)
```

### Playwright browser not found

```bash
# Verify browser installed in container
docker exec -it rag-chatbot ls /ms-playwright
```

### Ollama connection refused

```bash
# Ensure Ollama is running on host
ollama serve

# Test from inside container
docker exec -it rag-chatbot curl http://host.docker.internal:11434/api/tags
```

### Out of memory

```bash
# Check RAM usage
docker stats

# Switch to smaller model
# In .env: OLLAMA_MODEL=llama3.2:1b
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit changes: `git commit -m 'feat: add your feature'`
4. Push: `git push origin feature/your-feature`
5. Open a Pull Request

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 👤 Author

**Madan Lal** — Agentic AI Engineer

[![GitHub](https://img.shields.io/badge/GitHub-madan--genai-black?logo=github)](https://github.com/madan-genai)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?logo=linkedin)](https://linkedin.com/in/your-profile)

---

<div align="center">
  <sub>Built with ❤️ — fully local, fully open source</sub>
</div>
