# 🚀 MIRROR AI — Zero-Dollar Free-Tier Deployment Guide

This guide walks you through deploying the complete **MIRROR AI** platform for **$0 / month** using industry-standard free tiers:

- **Database:** [Neon PostgreSQL](https://neon.tech) (Free serverless Postgres)
- **Backend:** [Render](https://render.com) (Free web service with auto-deploy from GitHub)
- **Frontend:** [Vercel](https://vercel.com) (Free Next.js hosting with global CDN)

---

## Step 1: Deploy Database (Neon PostgreSQL) — 2 minutes

1. Sign up / log in to **[Neon.tech](https://neon.tech)** (free, no credit card required).
2. Click **Create Project** → Name it `mirror-ai`.
3. Under **Connection Details**, select **`SQLAlchemy`** or copy the **Connection string**:
   ```
   postgresql://user:password@ep-xyz.region.aws.neon.tech/mirror_ai?sslmode=require
   ```
4. Convert the prefix to async format:
   Change `postgresql://` to `postgresql+asyncpg://`
   *(Example: `postgresql+asyncpg://user:password@ep-xyz.region.aws.neon.tech/mirror_ai?sslmode=require`)*
5. Keep this `DATABASE_URL` handy for Step 2!

---

## Step 2: Deploy Backend (Render) — 3 minutes

1. Sign up / log in to **[Render.com](https://render.com)** using your GitHub account.
2. Click **New +** → **Web Service**.
3. Select **Build and deploy from a Git repository** → Select your repository:
   **`AyushYele25/MIRROR_AI-`**
4. Configure the service settings:
   - **Name:** `mirror-ai-backend`
   - **Region:** Any (e.g. Frankfurt or Oregon)
   - **Branch:** `main`
   - **Root Directory:** `backend`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** `Free`

5. Scroll down to **Environment Variables** and add:
   | Key | Value |
   |:---|:---|
   | `APP_ENV` | `production` |
   | `APP_DEBUG` | `false` |
   | `DATABASE_URL` | *(Paste your Neon connection string from Step 1)* |
   | `GITHUB_TOKEN` | *(Your GitHub PAT)* |
   | `CORS_ORIGINS` | `["*"]` |

6. Click **Create Web Service**.
7. Once deployed, Render will give you a public URL (e.g. `https://mirror-ai-backend.onrender.com`).
   Test it at: `https://mirror-ai-backend.onrender.com/health`

---

## Step 3: Deploy Frontend (Vercel) — 2 minutes

1. Sign up / log in to **[Vercel.com](https://vercel.com)** using your GitHub account.
2. Click **Add New...** → **Project**.
3. Import your GitHub repository: **`AyushYele25/MIRROR_AI-`**.
4. Configure Project:
   - **Framework Preset:** `Next.js`
   - **Root Directory:** Click **Edit** and select **`frontend`** 👈 *(Crucial!)*
5. Under **Environment Variables**, add:
   | Key | Value |
   |:---|:---|
   | `NEXT_PUBLIC_API_URL` | `https://mirror-ai-backend.onrender.com` *(Your Render backend URL)* |

6. Click **Deploy**.
7. Within 60 seconds, your portfolio dashboard will be live at `https://mirror-ai-xyz.vercel.app`! 🎉

---

## Architecture Summary

```
                                  +-----------------------+
                                  |  Vercel Global CDN    |
                                  |  Next.js 15 Frontend  |
                                  +-----------+-----------+
                                              |
                                              | REST / JSON
                                              v
+------------------------+        +-----------+-----------+
|    GitHub REST API     |<-------+     Render Web Svc    |
| (Rate-limited Client)  |        |    FastAPI Backend    |
+------------------------+        +-----------+-----------+
                                              |
                                              | Async SQLAlchemy
                                              v
                                  +-----------+-----------+
                                  |    Neon PostgreSQL    |
                                  |  (Serverless Storage) |
                                  +-----------------------+
```
