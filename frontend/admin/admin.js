const ADMIN_NAV = [
  { key: "dashboard", label: "Dashboard", href: "dashboard.html", icon: "home" },
  { key: "requisitions", label: "Requisitions", href: "requisitions.html", icon: "list" },
  { key: "tenders", label: "Tenders", href: "tenders.html", icon: "file" },
  { key: "finance", label: "Finance", href: "finance.html", icon: "tag" },
  { key: "inventory", label: "Inventory", href: "inventory.html", icon: "box" },
  { key: "users", label: "Users", href: "users.html", icon: "user" },
  { key: "remarks", label: "Remarks", href: "remarks.html", icon: "message" },
  { key: "audit", label: "Audit log", href: "audit.html", icon: "shield" },
];

const body = () => document.getElementById("pageBody");

async function renderDashboard() {
  const [reqs, tenders, payments, remarks] = await Promise.all([
    api.get("/requisitions/"),
    api.get("/tenders/open"),
    api.get("/finance/"),
    api.get("/remarks/"),
  ]);
  const undelivered = payments.filter((p) => !p.is_delivered);
  const followups = undelivered.filter((p) => p.phone_followup_required).length;
  setBody(body(), pageHead("Admin dashboard", "Overview of approvals, tenders, payments and remarks.") +
    `<div class="stats">
      ${statCard("Awaiting your signature", reqs.filter((r) => r.status === "PENDING_ADMIN").length, "Requisitions at admin stage", "check")}
      ${statCard("Open tenders", tenders.length, "Requisitions with quotations", "file")}
      ${statCard("Awaiting delivery", undelivered.length, `${followups} need a phone follow-up`, "box")}
      ${statCard("Open remarks", remarks.filter((r) => r.status !== "RESOLVED").length, "Not yet resolved", "message")}
    </div>`);
}

async function renderRequisitions() {
  const reqs = await api.get("/requisitions/");
  const rows = reqs.map((r) => `<tr>
      <td class="ref">${requestRef(r.id)}</td>
      <td>${escapeHtml(r.staff_name || "")}<div class="item-sub">${escapeHtml(r.department || "")}</div></td>
      <td>${escapeHtml(r.item_name || "")}</td>
      <td>${r.quantity_requested}</td>
      <td>${formatDate(r.created_at)}</td>
      <td>${statusPill(r.status)}</td>
      <td>${r.status === "PENDING_ADMIN"
        ? `<button class="btn btn-sm btn-primary" data-act="sign" data-id="${r.id}">Sign</button>
           <button class="btn btn-sm" data-act="decline" data-id="${r.id}">Decline</button>`
        : ""}</td>
    </tr>`).join("");
  setBody(body(), pageHead("Requisitions", "Sign off requests at admin stage, or decline them with a reason.") +
    dataTable(["Request ID", "Staff", "Item", "Qty", "Date", "Status", "Action"], rows, "No requisitions yet."));
  wireActions(body(), {
    sign: async (btn) => {
      await api.put(`/requisitions/${btn.dataset.id}/sign-admin`);
      return "Requisition signed off.";
    },
    decline: async (btn) => {
      const reason = window.prompt("Reason for declining (at least 3 characters)");
      if (!reason) throw new Error("Decline cancelled.");
      await api.put(`/requisitions/${btn.dataset.id}/decline`, { reason });
      return "Requisition declined.";
    },
  }, renderRequisitions);
}

async function renderTenders() {
  const tenders = await api.get("/tenders/open");
  const cards = tenders.map((t) => {
    const quoteRows = t.quotations.map((q) => `<tr>
        <td>${escapeHtml(q.supplier_name)}<div class="item-sub">${escapeHtml(q.supplier_email)}</div></td>
        <td>${money(q.total_price)}</td>
        <td>${formatDate(q.expected_delivery_date)}</td>
        <td>${q.is_compliant ? `<span class="pill approved">Compliant</span>` : `<span class="pill declined">Not compliant</span>`}</td>
        <td>${q.is_approved_lowest ? `<span class="pill fulfilled">Lowest</span>` : ""}</td>
        <td class="item-sub">${escapeHtml(q.ai_flag_notes || "")}</td>
        <td><button class="btn btn-sm btn-primary" data-act="pay" data-id="${q.id}" data-amount="${q.total_price}">Approve &amp; pay</button></td>
      </tr>`).join("");
    return `<div class="card table-card" style="margin-bottom:24px">
      <div class="card-body" style="display:flex;justify-content:space-between;align-items:center">
        <div><strong>${requestRef(t.requisition_id)}</strong> · ${escapeHtml(t.item_name)} × ${t.quantity_requested}</div>
        <button class="btn btn-sm" data-act="ai" data-id="${t.requisition_id}">Run AI check</button>
      </div>
      <table>
        <thead><tr><th>Supplier</th><th>Price</th><th>Delivery</th><th>Compliance</th><th>Ranking</th><th>AI notes</th><th>Action</th></tr></thead>
        <tbody>${quoteRows || `<tr><td class="empty-cell" colspan="7">No quotations yet.</td></tr>`}</tbody>
      </table>
    </div>`;
  }).join("");

  setBody(body(), pageHead("Tenders", "Compare supplier quotations, run the AI check and approve payment.") +
    (cards || `<div class="card card-body">No open tenders.</div>`) +
    formCard("Record a supplier quotation", [
      field("qReq", "Requisition ID", textInput("qReq", { type: "number", required: true, min: 1 })),
      field("qName", "Supplier name", textInput("qName", { required: true })),
      field("qEmail", "Supplier email", textInput("qEmail", { type: "email", required: true })),
      field("qPhone", "Supplier phone", textInput("qPhone", { required: true })),
      field("qDesc", "Quoted item description", textInput("qDesc", { required: true })),
      field("qPrice", "Total price (Rs)", textInput("qPrice", { type: "number", required: true, min: 0, step: "0.01" })),
      field("qDelivery", "Expected delivery", textInput("qDelivery", { type: "datetime-local", required: true })),
    ].join(""), "Save quotation", "quoteForm"));

  wireActions(body(), {
    ai: async (btn) => {
      await api.get(`/tenders/requisition/${btn.dataset.id}/ai-matrix`);
      return "AI compliance check complete.";
    },
    pay: async (btn) => {
      const cheque = window.prompt("Cheque number for this payment");
      if (!cheque) throw new Error("Payment cancelled.");
      await api.post("/finance/approve-and-pay", {
        quotation_id: Number(btn.dataset.id),
        cheque_number: cheque.trim(),
        amount_paid: Number(btn.dataset.amount),
      });
      return "Payment approved and recorded.";
    },
  }, renderTenders);

  onFormSubmit(document.getElementById("quoteForm"), async (data) => {
    await api.post("/tenders/quotations", {
      requisition_id: Number(data.get("qReq")),
      supplier_name: data.get("qName"),
      supplier_email: data.get("qEmail"),
      supplier_phone: data.get("qPhone"),
      quoted_item_description: data.get("qDesc"),
      total_price: Number(data.get("qPrice")),
      expected_delivery_date: data.get("qDelivery"),
    });
    return "Quotation saved.";
  }, renderTenders);
}

async function renderFinance() {
  const payments = await api.get("/finance/");
  const rows = payments.map((p) => `<tr>
      <td class="ref">PAY-${String(p.id).padStart(4, "0")}</td>
      <td>Quotation #${p.quotation_id}</td>
      <td>${escapeHtml(p.cheque_number)}</td>
      <td>${money(p.amount_paid)}</td>
      <td>${formatDate(p.payment_date)}</td>
      <td>${p.is_delivered
        ? `<span class="pill completed">Delivered</span>`
        : p.phone_followup_required
          ? `<span class="pill declined">Phone follow-up</span>`
          : `<span class="pill paid">Awaiting delivery</span>`}</td>
      <td>${p.is_delivered ? "" : `<button class="btn btn-sm btn-primary" data-act="deliver" data-id="${p.id}">Mark delivered</button>`}</td>
    </tr>`).join("");
  setBody(body(), pageHead("Finance", "Payments, deliveries and SLA follow-ups.",
      `<button class="btn" data-act="sla"><span data-icon="alert"></span>Run SLA checks</button>`) +
    dataTable(["Payment", "Quotation", "Cheque", "Amount", "Paid on", "Delivery", "Action"], rows, "No payments recorded yet."));
  wireActions(body(), {
    deliver: async (btn) => {
      await api.put(`/finance/deliveries/${btn.dataset.id}/complete`);
      return "Delivery marked complete.";
    },
    sla: async () => {
      const result = await api.post("/finance/run-sla-checks", {});
      return `SLA checks run: ${result.alerts_triggered} alert(s) raised.`;
    },
  }, renderFinance);
}

async function renderInventory() {
  const items = await api.get("/inventory/");
  const rows = items.map((i) => `<tr>
      <td class="ref">#${i.id}</td>
      <td>${escapeHtml(i.item_name)}</td>
      <td>${escapeHtml(i.department_category)}</td>
      <td>${escapeHtml(i.sub_category || "")}</td>
      <td>${i.quantity_in_stock}</td>
    </tr>`).join("");
  setBody(body(), pageHead("Inventory", "Stationery items and stock on hand.") +
    dataTable(["Item ID", "Item", "Category", "Sub-category", "In stock"], rows, "No items yet.") +
    formCard("Add an item", [
      field("iName", "Item name", textInput("iName", { required: true })),
      field("iCat", "Department category", textInput("iCat", { required: true })),
      field("iSub", "Sub-category (optional)", textInput("iSub")),
      field("iQty", "Quantity in stock", textInput("iQty", { type: "number", required: true, min: 0 })),
    ].join(""), "Add item", "itemForm"));

  onFormSubmit(document.getElementById("itemForm"), async (data) => {
    await api.post("/inventory/", {
      item_name: data.get("iName").trim(),
      department_category: data.get("iCat").trim(),
      sub_category: data.get("iSub").trim() || null,
      quantity_in_stock: Number(data.get("iQty")),
    });
    return "Item added.";
  }, renderInventory);
}

async function renderUsers() {
  const users = await api.get("/users/");
  const rows = users.map((u) => `<tr>
      <td>${escapeHtml(u.full_name)}</td>
      <td>${escapeHtml(u.email)}</td>
      <td>${escapeHtml(u.department)}</td>
      <td><span class="pill">${escapeHtml(u.role)}</span></td>
    </tr>`).join("");
  setBody(body(), pageHead("Users", "Staff, department heads and administrators.") +
    dataTable(["Name", "Email", "Department", "Role"], rows, "No users yet.") +
    formCard("Create a user", [
      field("uName", "Full name", textInput("uName", { required: true })),
      field("uEmail", "Email", textInput("uEmail", { type: "email", required: true })),
      field("uDept", "Department", textInput("uDept", { required: true })),
      field("uRole", "Role", selectInput("uRole", [["STAFF", "Staff"], ["DEPT_HEAD", "Department head"], ["ADMIN", "Administrator"]])),
      field("uPass", "Initial password (min 8)", textInput("uPass", { type: "password", minlength: 8 })),
    ].join(""), "Create user", "userForm"));

  onFormSubmit(document.getElementById("userForm"), async (data) => {
    const password = data.get("uPass");
    await api.post("/users/", {
      full_name: data.get("uName").trim(),
      email: data.get("uEmail").trim(),
      department: data.get("uDept").trim(),
      role: data.get("uRole"),
      ...(password ? { password } : {}),
    });
    return "User created.";
  }, renderUsers);
}

async function renderRemarks() {
  const remarks = await api.get("/remarks/");
  const rows = remarks.map((r) => `<tr>
      <td>${escapeHtml(r.staff_name || "")}<div class="item-sub">${formatDate(r.created_at)}</div></td>
      <td>${escapeHtml(r.category)}<div class="item-sub">${escapeHtml(r.subject)}</div></td>
      <td class="item-sub">${escapeHtml(r.description)}</td>
      <td><select class="input remark-status">
        ${["PENDING_REVIEW", "IN_PROGRESS", "RESOLVED"].map((s) => `<option value="${s}" ${s === r.status ? "selected" : ""}>${s.replace("_", " ")}</option>`).join("")}
      </select></td>
      <td><input class="input remark-reply" maxlength="500" value="${escapeHtml(r.admin_response || "")}" placeholder="Response to staff"></td>
      <td><button class="btn btn-sm btn-primary" data-act="saveRemark" data-id="${r.id}">Save</button></td>
    </tr>`).join("");
  setBody(body(), pageHead("Remarks", "Review staff remarks, update their status and reply.") +
    dataTable(["Staff", "Category / subject", "Remark", "Status", "Response", ""], rows, "No remarks yet."));
  wireActions(body(), {
    saveRemark: async (btn) => {
      const row = btn.closest("tr");
      await api.put(`/remarks/${btn.dataset.id}/status`, {
        status: row.querySelector(".remark-status").value,
        admin_response: row.querySelector(".remark-reply").value.trim() || null,
      });
      return "Remark updated.";
    },
  }, renderRemarks);
}

async function renderAudit() {
  const logs = await api.get("/finance/audit-logs");
  const rows = logs.map((l) => `<tr>
      <td>${formatDate(l.created_at)}</td>
      <td>${escapeHtml(l.actor_role || "System")}</td>
      <td>${escapeHtml(l.action)}</td>
      <td>${escapeHtml(l.entity)}${l.entity_id ? ` #${l.entity_id}` : ""}</td>
      <td class="item-sub">${escapeHtml(l.details || "")}</td>
    </tr>`).join("");
  setBody(body(), pageHead("Audit log", "Recorded actions across requisitions, tenders and payments.") +
    dataTable(["When", "Actor", "Action", "Entity", "Details"], rows, "No audit entries yet."));
}

const PAGES = {
  dashboard: { title: "Admin dashboard", render: renderDashboard },
  requisitions: { title: "Requisitions", render: renderRequisitions },
  tenders: { title: "Tenders", render: renderTenders },
  finance: { title: "Finance", render: renderFinance },
  inventory: { title: "Inventory", render: renderInventory },
  users: { title: "Users", render: renderUsers },
  remarks: { title: "Remarks", render: renderRemarks },
  audit: { title: "Audit log", render: renderAudit },
};

(async () => {
  const key = document.body.dataset.page;
  const page = PAGES[key];
  const me = await loadCurrentStaff();
  if (!me) return;
  if (me.role !== "ADMIN") {
    location.href = roleHome(me.role);
    return;
  }
  renderShell(key, page.title, ADMIN_NAV, "ADMIN PORTAL");
  try {
    await page.render();
  } catch (error) {
    flash("error", error.message);
  }
})();
