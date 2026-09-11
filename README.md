# 🎓 Admission Guru

A web app that helps Maharashtra students find eligible colleges based on their MHT-CET / Diploma / Pharmacy cutoff data for 2025.

Supports **CET Engineering**, **DSY Engineering**, **Diploma (Post-SSC)**, **Pharmacy**, and **DSY Pharmacy** admission rounds.

---

## Features

- Predict eligible colleges from ~89,769 cutoff records across all CAP rounds
- Filter by branch, category, college type, gender, home university, and TFWS
- Safe / Moderate / Ambitious chance labels per college
- Download results as a formatted PDF
- User accounts to save and revisit college preference lists

---

## Project Structure

```
admission-guru/
├── backend/                  # Flask API server
│   ├── app.py                # All API routes
│   ├── auth.py               # User auth (SQLite + JWT)
│   ├── data_parser.py        # CSV parsers & in-memory cache
│   ├── predictor.py          # Filtering & ranking engine
│   └── pdf_gen.py            # PDF generation (ReportLab)
│
├── frontend/                 # Static frontend (served by Flask)
│   ├── index.html            # Landing page
│   ├── css/
│   │   ├── main.css
│   │   ├── auth.css
│   │   └── predict.css
│   ├── js/
│   │   ├── auth-state.js
│   │   └── predict.js
│   └── pages/
│       ├── predict.html
│       ├── login.html
│       ├── signup.html
│       ├── dashboard.html
│       ├── forgot.html
│       └── about.html
│
├── data/                     # Cutoff CSV data files (2025)
│   ├── CAP_All_Rounds_2025.csv
│   ├── 2025PHARMA_CAP*.csv.xls
│   ├── DSY round * cap.csv.xls
│   ├── Diploma 25 round *.csv.xls
│   └── DSY pharmacy round 2 25.csv.xls
│
├── start_server.py           # Entry point — run this to start the app
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variable template
└── .gitignore
```

---

## Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/your-username/admission-guru.git
cd admission-guru
```

### 2. Create and activate a virtual environment (recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment (optional)

```bash
cp .env.example .env
# Edit .env and set your own SECRET_KEY for production
```

### 5. Start the server

```bash
python start_server.py
```

### 6. Open the app

```
http://localhost:5000
```

The SQLite database (`backend/admissionguru.db`) is created automatically on first run.

---

## API Endpoints

| Method | Route | Auth | Description |
|--------|-------|------|-------------|
| GET | `/api/health` | — | Server health check |
| POST | `/api/auth/register` | — | Register a new user |
| POST | `/api/auth/login` | — | Login, returns JWT token |
| GET | `/api/auth/me` | JWT | Get current user info |
| GET | `/api/meta/<exam_type>` | — | Dropdown data for a given exam |
| POST | `/api/predict` | — | Get ranked college list |
| POST | `/api/pdf` | — | Download results as PDF |
| GET | `/api/lists` | JWT | Get saved college lists |
| POST | `/api/lists` | JWT | Save a college list |
| DELETE | `/api/lists/<id>` | JWT | Delete a saved list |

Valid `exam_type` values: `CET`, `Pharmacy`, `DSY_Engineering`, `Diploma`, `DSY_Pharmacy`

---

## Data Files

All cutoff files are plain CSV text (some carry a `.csv.xls` extension — they are still read as CSV). Total: **89,769 records**.

| File | Exam | Records |
|------|------|---------|
| `CAP_All_Rounds_2025.csv` | CET Engineering | 34,284 |
| `2025PHARMA_CAP*.csv.xls` | Pharmacy | 10,854 |
| `DSY round * cap.csv.xls` | DSY Engineering | 15,735 |
| `Diploma 25 round *.csv.xls` | Diploma | 27,915 |
| `DSY pharmacy round 2 25.csv.xls` | DSY Pharmacy | 981 |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.10+, Flask 3.1, Flask-CORS |
| Auth | bcrypt, PyJWT |
| Database | SQLite (via Python `sqlite3`) |
| PDF | ReportLab |
| Frontend | Vanilla HTML / CSS / JavaScript |

---

## Requirements

- Python 3.10 or higher
- See `requirements.txt` for all packages

---

## License

MIT
