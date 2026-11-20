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
| `database.py` | Loads `config/.env`, creates the SQLAlchemy engine, and adds missing columns to existing tables. |
| `security.py` | PBKDF2-SHA256 password hashing, HMAC-signed bearer tokens (8 hour TTL), and the `require_roles` dependency. |
| `auth/`, `users/` | Login, `/auth/me`, and user management (ADMIN). |
| `inventory/` | Stationery items and stock levels. |
| `requisitions/` | Requests and signatures: head sign-off, admin sign-off, decline. List and progress endpoints are scoped to the caller. |
| `tenders/` | Supplier quotations, open tenders, the AI matrix, and compliance checks (`ai_engine.py`). |
| `finance/` | Approve-and-pay, deliveries, SLA checks (`scheduler.py`), and the audit log view. |
| `remarks/` | Staff remarks, admin responses, and attachments (PDF/JPG/PNG, stored in the database, max 5 per remark, 10 MB each). |
| `audit.py`, `notifications.py` | Audit trail writes, and SMTP email (logs instead of sending when SMTP is not configured). |

## Roles and workflow

Roles are `STAFF`, `DEPT_HEAD` and `ADMIN`.

1. STAFF create a requisition (`PENDING_HEAD`).
2. DEPT_HEAD sign off (`PENDING_ADMIN`), or decline.
3. ADMIN sign off. If stock covers the request it becomes `FULFILLED_FROM_STOCK`. Otherwise it becomes `TENDER_OPEN`. ADMIN can also decline.
4. For an open tender, quotations are recorded and checked for compliance. Only the lowest compliant quotation can be approved and paid, once per requisition, with a unique cheque number (`PAID_AWAITING_DELIVERY`).
5. ADMIN marks the delivery complete (`COMPLETED`). The SLA loop sends a pre-delivery reminder within 24 hours of the due date, and flags a phone follow-up when the order is overdue.

## Data and locking

* `create_all` creates new tables but does not add columns. New columns on existing tables must be added to `MISSING_COLUMNS` in `database.py`.
* Stock deduction and payment use `with_for_update()`, which only locks on MySQL. SQLite ignores it, so concurrency protection must be tested against MySQL.

## Frontend (`frontend/`)

* `index.html` signs the user in and redirects to the portal for their role.
* `assets/js/api.js` wraps `fetch` with the token, and redirects to login on 401.
* `staff/staff.js` provides the shared shell, navigation, status pills and the progress tracker.
* `assets/js/portal.js` provides table, form and action helpers for the admin and department-head portals.
* Pages: `staff/` (dashboard, create request, request history, remarks, manage profile), `dept-head/dashboard.html`, and `admin/` (dashboard, requisitions, tenders, finance, inventory, users, remarks, audit log).

## Tests

`tests/` runs against an in-memory SQLite database. `tests/conftest.py` seeds users and departments. `tests/test_workflow.py` covers the SRS workflow, RBAC, scoping, remarks, payments and deliveries.
