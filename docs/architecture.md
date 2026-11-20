# Architecture

## Overview

The MCIA procurement system is a FastAPI backend with a MySQL database (SQLite is used only by the tests) and a static HTML/CSS/JavaScript frontend. The frontend calls the API over HTTP with a bearer token.

```
frontend/ (static, port 5500)  --HTTP/JSON-->  src/app (FastAPI, port 8000)  -->  MySQL
                                                   |-- Gemini API (quotation checks, optional)
                                                   |-- SMTP (notifications, optional)
```

## Backend modules (`src/app/`)

| Module | Responsibility |
| --- | --- |
| `main.py` | App wiring, CORS for localhost and 127.0.0.1, router registration, and the SLA loop started in the lifespan hook. |
| `database.py` | Loads `config/.env`, creates the SQLAlchemy engine, adds missing columns, and idempotently backfills legacy one-item requisitions/quotations into line tables. |
| `security.py` | PBKDF2-SHA256 password hashing, HMAC-signed bearer tokens (8 hour TTL), and the `require_roles` dependency. |
| `auth/`, `users/` | Login, `/auth/me`, and user management (ADMIN). |
| `inventory/` | Stationery items and stock levels. |
| `requisitions/` | Multi-item requests, Head/Admin approvals, quotation handoff, decline, and per-line stock/tender status. List and progress endpoints are scoped to the caller. |
| `tenders/` | Staff-submitted supplier packages with selected item lines, open tenders, comparative tables, and per-line compliance checks (`ai_engine.py`). |
| `finance/` | Per-tender-line approve-and-pay, deliveries, SLA checks (`scheduler.py`), and the audit log view. |
| `remarks/` | Staff remarks, admin responses, and attachments (PDF/JPG/PNG, stored in the database, max 5 per remark, 10 MB each). |
| `audit.py`, `notifications.py` | Audit trail writes, and SMTP email (logs instead of sending when SMTP is not configured). |

## Roles and workflow

Roles are `STAFF`, `DEPT_HEAD` and `ADMIN`.

1. STAFF submit a multi-line requisition (`PENDING_HEAD`).
2. DEPT_HEAD approves or declines. Approved requests with shortage lines move to `PENDING_QUOTES`; requests with sufficient stock move to `PENDING_ADMIN`.
3. STAFF record one or more supplier packages. Each package can cover selected shortage lines and carries a separate price for each line. Every line requiring tender needs at least one quote before staff can send the package to Admin.
4. ADMIN reviews the line-by-line comparative table and signs or declines. Stock is rechecked under row locks: fully available lines are deducted; only shortage lines become `TENDER_OPEN`.
5. For each tendered line, only the lowest compliant quote can be paid, once per line, with a unique cheque number. Delivery completion updates each line and the request; the SLA loop reminds before due dates and flags overdue follow-up.

## Data and locking

* `create_all` creates new tables but does not add columns. New columns on existing tables must be added to `MISSING_COLUMNS` in `database.py`. Startup backfills legacy single-item requests and quotations into their new line tables.
* Stock deduction and payment use `with_for_update()`, which only locks on MySQL. SQLite ignores it, so concurrency protection must be tested against MySQL.

## Frontend (`frontend/`)

* `index.html` signs the user in and redirects to the portal for their role.
* `assets/js/api.js` wraps `fetch` with the token, and redirects to login on 401.
* `staff/staff.js` provides the shared shell, navigation, status pills and the progress tracker.
* `assets/js/portal.js` provides table, form and action helpers for the admin and department-head portals.
* Pages: `staff/` (dashboard, create request, request history, remarks, manage profile), `dept-head/dashboard.html`, and `admin/` (dashboard, requisitions, tenders, finance, inventory, users, remarks, audit log).

## Tests

`tests/` runs against an in-memory SQLite database. `tests/conftest.py` seeds users and departments. `tests/test_workflow.py` covers the SRS workflow, RBAC, scoping, remarks, payments and deliveries.
