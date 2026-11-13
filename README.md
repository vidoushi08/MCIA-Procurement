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
   git clone https://github.com
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
   DATABASE_URL=mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/mcia_procurement
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

5. **Create the MySQL database:**
   Run `CREATE DATABASE mcia_procurement;` in MySQL Workbench.

6. **Start the FastAPI server:**
   ```powershell
   .\venv\Scripts\python.exe -m uvicorn src.app.main:app --reload
   ```
   Access the interactive API documentation at `http://127.0.0`.
