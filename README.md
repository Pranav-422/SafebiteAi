# 🥗 Safe Bite AI — Full Stack Setup Guide

> Smart Food Label & Allergy Risk Detection System  
> **Stack:** Next.js 14 · TypeScript · Tailwind CSS · Flask · MySQL · Tesseract OCR

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
│   ├── .env.local             ← NEXT_PUBLIC_API_URL
│   ├── next.config.js
│   ├── postcss.config.js
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── package.json
└── backend/                   ← Flask REST API
    ├── app.py                 ← All routes + safety engine + OCR
    ├── requirements.txt       ← Python dependencies
    └── schema.sql             ← MySQL database schema
```

---

## ⚙️ Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Node.js | 18 + | https://nodejs.org |
| Python | 3.10 + | https://python.org |
| MySQL | 8.0 + | https://dev.mysql.com |
| Tesseract OCR | 5.x | See below |

### Install Tesseract OCR

**macOS**
```bash
brew install tesseract
```

**Ubuntu / Debian**
```bash
sudo apt update && sudo apt install -y tesseract-ocr
```

**Windows**
Download installer: https://github.com/UB-Mannheim/tesseract/wiki  
Add to PATH: `C:\Program Files\Tesseract-OCR`

---

## 🗄️ 1. Database Setup (MySQL)

```bash
# Log into MySQL
mysql -u root -p

# Create database and user
CREATE DATABASE safebite_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'safebite'@'localhost' IDENTIFIED BY 'safebite123';
GRANT ALL PRIVILEGES ON safebite_db.* TO 'safebite'@'localhost';
FLUSH PRIVILEGES;
EXIT;

# Import schema
mysql -u safebite -p safebite_db < backend/schema.sql
```

---

## 🐍 2. Backend Setup (Flask)

```bash
# Navigate to backend
cd backend

# Create and activate virtual environment
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configure environment variables

Create a `.env` file inside `backend/`:

```env
DB_HOST=localhost
DB_USER=safebite
DB_PASS=safebite123
DB_NAME=safebite_db
JWT_SECRET=your-super-secret-key-change-in-production
```

### Run the Flask server

```bash
# Development (auto-reload)
python app.py

# OR with Flask CLI
flask --app app run --debug --port 5000
```

Flask will be live at: **http://localhost:5000**

Verify: http://localhost:5000/api/health → `{"status":"ok","version":"1.0.0"}`

---

## ⚡ 3. Frontend Setup (Next.js)

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Verify .env.local has correct backend URL
cat .env.local
# Should output: NEXT_PUBLIC_API_URL=http://localhost:5000/api
```

### Run the development server

```bash
npm run dev
```

App will be live at: **http://localhost:3000**

---

## 🚀 Running Both Together

Open **two terminal windows**:

**Terminal 1 — Backend**
```bash
cd backend
source venv/bin/activate      # or venv\Scripts\activate on Windows
python app.py
```

**Terminal 2 — Frontend**
```bash
cd frontend
npm run dev
```

Then open **http://localhost:3000** in your browser.

---

## 📦 Production Build

### Frontend
```bash
cd frontend
npm run build      # Compiles + optimises
npm run start      # Serves production build on port 3000
```

### Backend (with Gunicorn)
```bash
cd backend
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

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
| POST | `/api/auth/login` | ❌ | Get JWT token |
| GET | `/api/user/profile` | ✅ | Fetch profile |
| PUT | `/api/user/profile` | ✅ | Update profile + restrictions |
| GET | `/api/products` | ❌ | List products |
| GET | `/api/products/barcode/:code` | ❌ | Find by barcode |
| POST | `/api/analyze/text` | ✅ | Analyse typed ingredients |
| POST | `/api/analyze/image` | ✅ | Analyse image (base64) |
| POST | `/api/analyze/product/:id` | ✅ | Analyse DB product |
| GET | `/api/history` | ✅ | Scan history |
| GET | `/api/ingredients` | ❌ | Ingredients reference |
| GET | `/api/health` | ❌ | Health check |

---

## 🔐 Auth Flow

1. Register / login → receive JWT token
2. Token stored in `localStorage` as `safebite_token`
3. All `✅` endpoints require `Authorization: Bearer <token>` header
4. Token expires after **24 hours**

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

## 🐛 Troubleshooting

**`pytesseract.TesseractNotFoundError`**  
→ Tesseract is not in PATH. Run `tesseract --version` to verify. On Windows set the full path in `app.py`:
```python
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

**`Access to fetch blocked by CORS`**  
→ Ensure Flask is running on port 5000 and `.env.local` has `NEXT_PUBLIC_API_URL=http://localhost:5000/api`

**`Can't connect to MySQL`**  
→ Check `DB_HOST`, `DB_USER`, `DB_PASS`, `DB_NAME` in `backend/.env`

**`Module not found: @/components/...`**  
→ Ensure `tsconfig.json` has `"paths": { "@/*": ["./*"] }` — already set.

---

## 📝 Notes

- Analysis results are stored in `sessionStorage` under `safebite_result` — they clear when the browser tab closes.
- The safety score formula: `score = max(0, 100 - (total_risk / 60) * 100)` — tune the `60` divisor in `app.py` to adjust sensitivity.
- Add seed ingredient data via `schema.sql` or through the MySQL CLI for meaningful scan results.
