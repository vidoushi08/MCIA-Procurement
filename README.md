# MCIA Low-Value Stationery E-Procurement & Inventory Management Platform

An AI-powered internal procurement and inventory system developed during an internship placement at the **Mauritius Cane Industry Authority (MCIA)**. 

This platform digitizes low-value office stationery requests, enforces multi-tier digital signatures, automates live stock deductions, evaluates out-of-stock supplier quotations using Google Gemini AI, and tracks delivery Service Level Agreements (SLAs).

---

## Core System Workflow

1. **Department-Categorized Requisition & 3-Tier Signatures:** Staff filter office stationery by department, submit a digital request form, and apply the first signature. Requests route to the **Department Head** (2nd signature) and **Administrator / Head of Procurement** (3rd signature), with a **live progress tracker** visible to staff.
2. **Automated Stock Check & Deduction:** Upon Administrator signature, the system verifies live MySQL stock levels. If available, quantities are atomically deducted and issued. If out of stock, the request automatically opens for supplier tendering.
3. **AI-Powered Quotation Matrix:** Staff log vendor quotes (including supplier email and phone contacts). The **Google Gemini AI Engine** flags item discrepancies and generates a **Lowest-Cost Comparative Table**.
4. **Cheque Issuance & SLA Reminders:** The Administrator approves the lowest-cost compliant bid and records the **issued cheque number**. Automated background reminders alert staff/admins before the due date and dispatch overdue emails/phone flags if deadlines are breached.

---

## Technology Stack

* **Backend Framework:** Python 3.11+, FastAPI, Pydantic
* **Database & ORM:** MySQL 8.0, SQLAlchemy, PyMySQL
* **Artificial Intelligence:** Google Gemini API (`google-genai`)
* **Frontend:** HTML5, CSS3, JavaScript
* **Version Control:** Git & GitHub

---

## Local Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/vidoushi08/MCIA-Procurement.git
   cd MCIA-Procurement
   ```

2. **Create and activate a virtual environment:**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```powershell
   .\venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

4. **Configure environment variables (`config/.env`):**
   ```text
   DATABASE_URL=mysql+pymysql://mcia_app:YOUR_APP_PASSWORD@localhost:3306/mcia_procurement
   GEMINI_API_KEY=your_gemini_api_key_here
   APP_SECRET_KEY=a_long_random_string
   SMTP_HOST=smtp.example.com
   SMTP_FROM=procurement@example.com
   ```
   Use a dedicated application user rather than `root`. Do not commit this file. See `config/.env.example` for every option, including `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SLA_CHECK_ENABLED` and `SLA_CHECK_INTERVAL_MINUTES`.

   | Variable | Purpose |
   | --- | --- |
   | `DATABASE_URL` | MySQL connection string (required). |
   | `APP_SECRET_KEY` | Signs login tokens. Set it, or tokens become invalid on every server restart. |
   | `GEMINI_API_KEY` | Enables Gemini quotation checks. A local fallback check runs without it. |
   | `SMTP_HOST`, `SMTP_FROM` (plus optional `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`) | Sends email notifications. Without them, notifications are logged only. |
   | `SLA_CHECK_ENABLED`, `SLA_CHECK_INTERVAL_MINUTES` | Background SLA reminder loop (default on, every 60 minutes). |

5. **Create the MySQL database and application user:**
   ```sql
   CREATE DATABASE mcia_procurement;
   CREATE USER 'mcia_app'@'localhost' IDENTIFIED BY 'YOUR_APP_PASSWORD';
   GRANT ALL PRIVILEGES ON mcia_procurement.* TO 'mcia_app'@'localhost';
   ```

6. **Start the FastAPI server:**
   ```powershell
   .\venv\Scripts\python.exe -m uvicorn src.app.main:app --reload
   ```
   Access the interactive API documentation at `http://127.0.0.1:8000/docs`.

7. **Serve the frontend (separate terminal):**
   ```powershell
   cd frontend
   python -m http.server 5500
   ```
   Open `http://127.0.0.1:5500/index.html` and sign in. Each role lands on its own portal: `staff/`, `dept-head/` or `admin/`.

8. **Set a user's password** (run once per user, passing their email):
   ```powershell
   .\venv\Scripts\python.exe scripts\set_password.py someone@example.com
   ```

---

## Running the Tests

The suite uses an in-memory SQLite database, so it needs no MySQL server or Gemini key:

```powershell
.\venv\Scripts\python.exe -m pytest -q -p no:warnings
```

---

## Documentation

* [User manual](docs/USER_MANUAL.md): step-by-step guide for staff, department heads and administrators.
* [Architecture](docs/architecture.md): backend modules, data model and workflow rules.
