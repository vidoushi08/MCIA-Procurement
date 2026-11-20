# MCIA Procurement: User Manual

This manual covers day-to-day use of the stationery e-procurement system for staff, department heads and administrators.

## 1. Getting started

1. Start the backend API (port 8000) and the static frontend server (port 5500), as described in the [README](../README.md).
2. Open `http://127.0.0.1:5500/` in your browser.
3. Sign in with your email and password. Your password is set by an administrator with `scripts\set_password.py <email>`.
4. You are taken to the portal for your role:
   * **Staff**: `frontend/staff/dashboard.html`
   * **Department head**: `frontend/dept-head/dashboard.html`
   * **Administrator**: `frontend/admin/dashboard.html`

Sessions last 8 hours. If your session expires, you are sent back to the sign-in page.

## 2. Staff

### Create a request
1. Open **Create request** and choose the items and quantities you need.
2. Submit the request. It starts at *Pending head approval*.

### Track requests
* **Request history** lists all your requests with their status.
* The **dashboard** shows the progress tracker for your latest request.

Request stages, in order: pending head approval, pending admin approval, then either fulfilled from stock or tender open. For tendered items: paid, awaiting delivery, then completed. A request can also be declined at the head or admin stage. The reason is shown on the request.

### Remarks
Use **Remarks** to send a complaint or comment to the administrators. Give a category, a subject and a description of at least 10 characters. You can attach up to 5 PDF, JPG or PNG files, each up to 10 MB. You can see the status of your remarks (pending review, in progress, resolved), open your attachments, and read any admin response.

### Log a quotation
When a supplier quotation arrives for an open tender, open **Log quotation**. Enter the requisition ID, the supplier's details, the quoted item, the total price and the expected delivery date. The administrator then reviews it and runs the compliance check.

### Manage profile
Update your contact details from **Manage profile**.

## 3. Department head

1. The **dashboard** shows the **pending approval queue**: requests from your department waiting for your sign-off.
2. To approve, select **Approve**. The request moves to admin approval.
3. To decline, select **Decline** and enter a reason. The staff member sees the reason.
4. The lower list shows all requests from your department. You only see your own department's requests.

## 4. Administrator

### Requisitions
Approve or decline requests that have passed head approval. If stock covers the request, it is fulfilled from stock. Otherwise a tender is opened.

### Tenders
1. Record each supplier quotation for an open tender.
2. Run the **AI compliance check** on each quotation. The check uses Gemini, which must be configured (see section 6).
3. Only a compliant quotation can be approved, and only the lowest compliant quotation can be paid.

### Finance
1. Approve and pay the chosen quotation. Each requisition is paid once. Each cheque number must be unique.
2. After the supplier delivers, confirm the delivery. This completes the requisition.
3. Watch the **SLA alerts**. A reminder is raised within 24 hours of the due date. If an order is overdue, it is flagged for a phone follow-up.

### Inventory
Add stationery items and update stock levels.

### Users
Create users, assign roles (staff, department head, administrator) and departments. Assign the password with `scripts\set_password.py <email>` on the server.

### Remarks
Review staff remarks, set the status (pending review, in progress, resolved) and write a response of up to 500 characters.

### Audit log
View a record of significant actions, such as approvals, payments and deliveries, with who made them and when.

## 5. Notifications

Email notifications are sent only when SMTP is configured in `config/.env`. Without SMTP, the system writes the notification to the server log instead, and nothing is emailed.

## 6. Setup items that need an administrator

These must be done by the system owner before the system is fully working:

| Item | Where | Effect if missing |
| --- | --- | --- |
| MySQL user `mcia_app` | Database | Backend cannot start with MySQL. |
| `APP_SECRET_KEY` | `config/.env` | Sign-in tokens are invalid after each server restart. |
| `GEMINI_API_KEY` | `config/.env` | AI compliance checks on quotations do not work. |
| `SMTP_HOST`, `SMTP_FROM` (and related SMTP settings) | `config/.env` | Email notifications are logged, not sent. |
| User passwords | `scripts\set_password.py <email>` | Users cannot sign in. |

## 7. Troubleshooting

* **Signed out unexpectedly**: sessions last 8 hours, and tokens are invalid after a restart if `APP_SECRET_KEY` is not set.
* **"Access denied" on a page**: your role does not have access to that portal. Sign in with the correct account.
* **Page is blank or stale**: refresh the page. Check that the API is running on port 8000.
* **Browser shows CORS errors**: the frontend must be opened from `localhost` or `127.0.0.1`, not another address.
