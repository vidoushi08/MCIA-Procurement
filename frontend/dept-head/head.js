const HEAD_NAV = [
  { key: "dashboard", label: "Dashboard", href: "dashboard.html", icon: "home" },
];

const headBody = () => document.getElementById("pageBody");

async function renderHeadDashboard() {
  const reqs = await api.get("/requisitions/");
  const pending = reqs.filter((r) => r.status === "PENDING_HEAD");
  const row = (r, withActions) => `<tr>
      <td class="ref">${requestRef(r.id)}</td>
      <td>${escapeHtml(r.staff_name || "")}</td>
      <td>${requestItemsCell(r.items)}</td>
      <td>${formatDate(r.created_at)}</td>
      <td>${statusPill(r.status)}</td>
      ${withActions ? `<td>
        <button class="btn btn-sm btn-primary" data-act="approve" data-id="${r.id}">Approve</button>
        <button class="btn btn-sm" data-act="decline" data-id="${r.id}">Decline</button>
      </td>` : ""}
    </tr>`;

  setBody(headBody(), pageHead("Department requests", `Requests from ${session.user()?.department || "your department"}.`) +
    `<div class="stats">
      ${statCard("Awaiting your approval", pending.length, "Pending head sign-off", "clock")}
      ${statCard("All department requests", reqs.length, "Newest first", "list")}
    </div>
    <h2 class="section-title">Pending your approval</h2>
    ${dataTable(["Request ID", "Staff", "Requested items", "Date", "Status", "Action"],
      pending.map((r) => row(r, true)).join(""), "Nothing waiting for your approval.")}
    <h2 class="section-title">All department requests</h2>
    ${dataTable(["Request ID", "Staff", "Requested items", "Date", "Status"],
      reqs.map((r) => row(r, false)).join(""), "No requests from your department yet.")}`);

  wireActions(headBody(), {
    approve: async (btn) => {
      const req = await api.put(`/requisitions/${btn.dataset.id}/sign-head`);
      return req.status === "PENDING_QUOTES"
        ? "Request approved. The staff member can now collect quotes for out-of-stock items."
        : "Request approved and sent to Admin.";
    },
    decline: async (btn) => {
      const reason = window.prompt("Reason for declining (at least 3 characters)");
      if (!reason) throw new Error("Decline cancelled.");
      await api.put(`/requisitions/${btn.dataset.id}/decline`, { reason });
      return "Request declined.";
    },
  }, renderHeadDashboard);
}

(async () => {
  const me = await loadCurrentStaff();
  if (!me) return;
  if (me.role !== "DEPT_HEAD") {
    location.href = roleHome(me.role);
    return;
  }
  renderShell("dashboard", "Department head dashboard", HEAD_NAV, "DEPARTMENT HEAD PORTAL");
  try {
    await renderHeadDashboard();
  } catch (error) {
    flash("error", error.message);
  }
})();
