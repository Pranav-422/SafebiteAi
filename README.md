# 🥗 Safe Bite AI — Full Stack Setup Guide

> Smart Food Label & Allergy Risk Detection System  
> **Stack:** Next.js 16 · React 19 · TypeScript · Tailwind CSS · Flask · SQLite · Tesseract OCR

---

## 📁 Project Structure

```
safebite/
├── frontend/                  ← Next.js 14 App Router
│   ├── app/
│   │   ├── layout.tsx         ← Root layout (fonts, metadata)
│   │   ├── globals.css        ← Tailwind + custom animations
│   │   ├── page.tsx           ← Home / landing
│   │   ├── login/page.tsx     ← Auth page
│   │   ├── dashboard/page.tsx ← User dashboard + scan history
│   │   ├── scan/page.tsx      ← 📸 Image upload + OCR scan
│   │   ├── analyze/page.tsx   ← ✍️  Manual ingredient entry
│   │   ├── report/page.tsx    ← 📊 Analysis results report
│   │   └── products/page.tsx  ← Product browser
│   ├── components/
│   │   ├── Navbar.tsx
│   │   └── SafetyScoreCard.tsx
│   ├── lib/
│   │   └── api.ts             ← All API calls + TypeScript types
│   ├── .env.example           ← NEXT_PUBLIC_API_URL (copy to .env.local)
│   ├── next.config.js
│   ├── postcss.config.js
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── package.json
└── backend/                   ← Flask REST API
    ├── app.py                 ← Routes, auth, OCR
    ├── safety_engine.py       ← Parsing, matching, scoring
    ├── seed_data.py           ← Allergens, aliases, animal-derived data
    ├── tests/                 ← pytest regression suite
    ├── requirements.txt       ← Python dependencies
    └── schema.sql             ← SQLite schema (auto-applied on start)
```

---

## ⚙️ Prerequisites

| Tool | Version |
|------|---------|
| Node.js | 20+ (22 recommended) |
| Python | 3.12 |
| Tesseract OCR | 5.x |

The backend uses **SQLite**. The database file is created and seeded automatically on first start, so no manual DB setup is needed.

### Install Tesseract OCR

- **macOS:** `brew install tesseract`
- **Ubuntu / Debian:** `sudo apt install -y tesseract-ocr`
- **Windows:** https://github.com/UB-Mannheim/tesseract/wiki (default path `C:\Program Files\Tesseract-OCR` is auto-detected)

---

## 🐍 1. Backend (Flask)

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scriptsctivate
pip install -r requirements-dev.txt

cp .env.example .env              # Windows: copy .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"   # paste into JWT_SECRET in .env

python app.py                     # http://localhost:5000/api/health
```

The app **refuses to start** without a `JWT_SECRET` of at least 32 characters.

Run the tests:

```bash
python -m pytest -q
```

## ⚡ 2. Frontend (Next.js)

```bash
cd frontend
cp .env.example .env.local        # NEXT_PUBLIC_API_URL=http://localhost:5000/api
npm install
npm run dev                       # http://localhost:3000
```

Checks: `npm run typecheck`, `npm run lint`, `npm run build`.

---

## 📦 Production

### Docker (recommended)

```bash
cp backend/.env.example backend/.env   # set JWT_SECRET, CORS_ORIGINS
docker compose up --build
```

- **backend/Dockerfile:** Python 3.12 + Tesseract, non-root user, gunicorn, SQLite stored on the `/data` volume
- **frontend/Dockerfile:** Next.js standalone build. `NEXT_PUBLIC_API_URL` is a **build argument**.
- **redis:** shared rate-limit storage for multiple gunicorn workers/instances

### Production checklist

- [ ] `JWT_SECRET` set from a secret manager (never committed)
- [ ] `CORS_ORIGINS` = your real frontend URL only
- [ ] HTTPS in front of both services; `TRUST_PROXY=1` when behind a load balancer
- [ ] `RATELIMIT_STORAGE_URI=redis://...` when running more than one worker or instance
- [ ] Persistent volume + backups for `DATABASE_PATH` (or migrate to PostgreSQL for multi-instance scale)
- [ ] `FLASK_DEBUG` unset or `0`
- [ ] Liveness probe `/api/health`, readiness probe `/api/ready`

### Hosting options

- **Simple:** Vercel (frontend) + Render / Railway / Fly.io (backend Docker image with a disk)
- **AWS:** Amplify or CloudFront (frontend) + App Runner / ECS Fargate (backend) + EFS volume or RDS

---

## 🗺️ Page Routes

| Route | Description |
|-------|-------------|
| `/` | Landing / home |
| `/login` | Register & login |
| `/dashboard` | User home + scan history |
| `/scan` | Upload food label photo → OCR |
| `/analyze` | Manually paste ingredient list |
| `/report` | Safety score + flagged ingredients |
| `/products` | Browse product library |

---

## 🔌 API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/register` | ❌ | Create account |
| POST | `/api/auth/login` | ❌ | Get JWT token (rate limited) |
| POST | `/api/auth/logout` | ✅ | Revoke current token |
| GET | `/api/user/profile` | ✅ | Fetch profile |
| PUT | `/api/user/profile` | ✅ | Update profile + restrictions |
| GET | `/api/products` | ❌ | List products |
| GET | `/api/products/barcode/:code` | ❌ | Find by barcode |
| POST | `/api/analyze/text` | ✅ | Analyse typed ingredients |
| POST | `/api/analyze/image` | ✅ | Analyse image (multipart `image` or JSON `image_base64`) |
| POST | `/api/analyze/product/:id` | ✅ | Analyse DB product |
| GET | `/api/history` | ✅ | Scan history |
| GET | `/api/ingredients` | ❌ | Ingredients reference |
| GET | `/api/restrictions` | ❌ | Supported allergy / diet / health restrictions |
| GET | `/api/health` | ❌ | Liveness check |
| GET | `/api/ready` | ❌ | Readiness (DB + OCR) |

---

## 🔐 Auth Flow

1. Register / login → receive JWT token
2. Token stored in `localStorage` as `safebite_token`
3. All `✅` endpoints require `Authorization: Bearer <token>` header
4. Token expires after **24 hours** (`TOKEN_EXPIRY_HOURS`); logout revokes it on the server
5. Any `401` response clears the session and redirects to `/login`

---

## 🎨 Design System

All design tokens are defined in `tailwind.config.ts`:

| Token | Value | Usage |
|-------|-------|-------|
| `text-primary` | `#6945c7` | Purple brand colour |
| `gradient-bg` | `#6945c7 → #c9b6ff` | Buttons, hero sections |
| `bg-surface-container-lowest` | `#ffffff` | Cards |
| `font-headline` | Plus Jakarta Sans | Headings |
| `font-body` | Manrope | Body text |
| `custom-shadow` | 20px soft shadow | Card shadows |
| `fade-in` | 0.35s fadeIn | Page transitions |
| `ocr-scanner-line` | Animated purple beam | Scan page overlay |

---

## 🧠 How the safety score works (`backend/safety_engine.py`)

1. **Parse:** split the label text. Bracketed sub-ingredients are kept, E-numbers and INS codes (`E102`, `INS 102`, `(102)`) are normalised, and negations (`non-hydrogenated`, `msg free`) are ignored.
2. **Match:** compare against ingredient names, aliases (e.g. maida → wheat, vanaspati → hydrogenated oil, whey → milk) and E-numbers. The longest name wins, so `cocoa butter` is never read as dairy `butter`.
3. **Score (0–10):** the worst flagged ingredient counts fully and each additional one counts 70% of the previous. Adding harmless ingredients cannot dilute the risk.
4. **Overrides:** an allergen matching the user's profile caps the score at 1 (**unsafe**). A diet conflict (vegan/vegetarian) caps it at 3.

Reference data lives in `schema.sql` (additives) and `seed_data.py` (allergens, aliases, animal-derived ingredients). Both are applied idempotently on every start.

---

## 🐛 Troubleshooting

**`RuntimeError: JWT_SECRET must be set`**: create `backend/.env` from `.env.example` and set a long random secret.

**`OCR is not available on this server`**: Tesseract isn't installed or found. Set `TESSERACT_CMD` in `backend/.env`.

**CORS errors in the browser**: add your frontend origin to `CORS_ORIGINS` in `backend/.env`.

**`429 Too many requests`**: rate limit hit. Limits are configurable in `backend/.env`.

---

## 📝 Notes

- Analysis results are kept in `sessionStorage` under `safebite_result` and are cleared on logout or when the tab closes.
- SafeBite AI is informational only and not medical advice. Users with severe allergies must always read the printed label.
