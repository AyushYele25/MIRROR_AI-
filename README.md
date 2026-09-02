# MIRROR AI

> **"See how you build."** — An AI system that models observable software-engineering behavior from GitHub history and produces evidence-backed developer profiles.

🚧 **Under active development** — Phase 1: Foundation

## Quick Start

```bash
# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your settings
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Architecture

- **Backend:** Python + FastAPI + SQLAlchemy (async)
- **Frontend:** Next.js + TypeScript + Tailwind CSS
- **Database:** PostgreSQL (Neon)
- **ML:** scikit-learn
- **LLM:** Gemini (explanation only)

## License

MIT
