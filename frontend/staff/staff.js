const ICONS = {
  home: '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M9 22V12h6v10"/>',
  "plus-circle": '<circle cx="12" cy="12" r="10"/><path d="M12 8v8M8 12h8"/>',
  list: '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
  message: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21v-1a7 7 0 0 1 14 0v1"/>',
  logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5M21 12H9"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',
  calendar: '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
  "chevron-down": '<path d="M6 9l6 6 6-6"/>',
  "chevron-right": '<path d="M9 18l6-6-6-6"/>',
  eye: '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>',
  lock: '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
  mail: '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="M22 6l-10 7L2 6"/>',
  id: '<rect x="2" y="5" width="20" height="14" rx="2"/><path d="M7 10h4M7 14h6M16 10h2"/>',
  building: '<rect x="4" y="2" width="16" height="20" rx="1"/><path d="M9 22v-4h6v4M8 6h2M14 6h2M8 10h2M14 10h2M8 14h2M14 14h2"/>',
  box: '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><path d="M3.3 7L12 12l8.7-5M12 22V12"/>',
  clock: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
  check: '<path d="M20 6L9 17l-5-5"/>',
  "check-circle": '<circle cx="12" cy="12" r="10"/><path d="M9 12l2 2 4-4"/>',
  "x-circle": '<circle cx="12" cy="12" r="10"/><path d="M15 9l-6 6M9 9l6 6"/>',
  upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/>',
  file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/>',
  info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
  alert: '<path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/>',
  shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
  phone: '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7a2 2 0 0 1-.5 2.1L8 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.7.7a2 2 0 0 1 1.7 2z"/>',
  pin: '<path d="M21 10c0 7-9 13-9 13S3 17 3 10a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>',
  save: '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><path d="M17 21v-8H7v8M7 3v5h8"/>',
  x: '<path d="M18 6L6 18M6 6l12 12"/>',
  "arrow-right": '<path d="M5 12h14M12 5l7 7-7 7"/>',
  "sign-in": '<path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4M10 17l5-5-5-5M15 12H3"/>',
  tag: '<path d="M20.6 13.4l-7.2 7.2a2 2 0 0 1-2.8 0L2 12V2h10l8.6 8.6a2 2 0 0 1 0 2.8z"/><circle cx="7" cy="7" r="1.5"/>',
  hash: '<path d="M4 9h16M4 15h16M10 3L8 21M16 3l-2 18"/>',
  send: '<path d="M22 2L11 13M22 2l-7 20-4-9-9-4z"/>',
};

function iconSvg(name) {
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name] || ""}</svg>`;
}

function icon(name) {
  return `<span class="ic">${iconSvg(name)}</span>`;
}

function hydrateIcons(root = document) {
  root.querySelectorAll("[data-icon]").forEach((el) => {
    el.classList.add("ic");
    el.innerHTML = iconSvg(el.dataset.icon);
  });
}

const NAV_ITEMS = [
  { key: "dashboard", label: "Dashboard", href: "dashboard.html", icon: "home" },
  { key: "create", label: "Create request", href: "create-request.html", icon: "plus-circle" },
  { key: "history", label: "Request history", href: "request-history.html", icon: "list" },
  { key: "complaints", label: "Remarks", href: "complaints.html", icon: "message" },
  { key: "profile", label: "Manage profile", href: "manage-profile.html", icon: "user" },
];

function renderShell(activeKey, crumb) {
  const app = document.getElementById("app");
  const nav = NAV_ITEMS.map((item) => {
    // The complaints page is labelled "Complaints" in the designs; every other page uses "Remarks".
    const label = item.key === "complaints" && activeKey === "complaints" ? "Complaints" : item.label;
    return `
      <a href="${item.href}" class="${item.key === activeKey ? "active" : ""}">
        ${icon(item.icon)}<span>${label}</span>
      </a>`;
  }).join("");

  app.insertAdjacentHTML(
    "afterbegin",
    `<aside class="sidebar">
      <div class="brand"><img src="../assets/img/mcia-logo.png" alt="MCIA"></div>
      <div class="sidebar-label">STAFF PORTAL</div>
      <nav class="nav">${nav}</nav>
      <div class="sidebar-photo">
        <img src="../assets/img/sidebar-field.jpg" alt="">
        <div class="caption">
          <strong>Supporting the people who keep us growing.</strong>
          <span>MAURITIUS · MCIA</span>
        </div>
      </div>
      <button class="signout" id="signOut" type="button">${icon("logout")}<span>Sign out</span></button>
    </aside>`
  );

  const content = app.querySelector(".content");
  content.insertAdjacentHTML(
    "afterbegin",
    `<header class="topbar">
      <div class="crumbs"><span>Procurement</span>${icon("chevron-right")}<strong>${escapeHtml(crumb)}</strong></div>
    </header>`
  );

  document.getElementById("signOut").addEventListener("click", signOut);
  hydrateIcons(app);
}

function signOut() {
  session.clear();
  location.href = "../index.html";
}

async function loadCurrentStaff() {
  const id = session.get();
  if (!id) {
    location.href = "../index.html";
    return null;
  }
  const users = await api.get("/users/");
  const me = users.find((u) => String(u.id) === String(id));
  if (!me) {
    session.clear();
    location.href = "../index.html";
    return null;
  }
  return me;
}

async function loadMyRequests(staffId) {
  const [requisitions, items] = await Promise.all([api.get("/requisitions/"), api.get("/inventory/")]);
  const itemById = new Map(items.map((item) => [item.id, item]));
  const mine = requisitions
    .filter((r) => String(r.staff_id) === String(staffId))
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    .map((r) => ({ ...r, item: itemById.get(r.item_id) }));
  return { mine, items };
}

const STATUS_MAP = {
  PENDING_HEAD: { group: "pending", label: "Pending review" },
  PENDING_ADMIN: { group: "pending", label: "Pending review" },
  TENDER_OPEN: { group: "approved", label: "Approved" },
  FULFILLED_FROM_STOCK: { group: "fulfilled", label: "Fulfilled" },
  DECLINED: { group: "declined", label: "Declined" },
};

function statusGroup(status) {
  return (STATUS_MAP[status] || { group: "pending" }).group;
}

function statusPill(status) {
  const info = STATUS_MAP[status] || { group: "pending", label: status };
  return `<span class="pill ${info.group}">${escapeHtml(info.label)}</span>`;
}

function requestRef(id) {
  return `REQ-${String(id).padStart(4, "0")}`;
}

function staffCode(id) {
  return `MCIA-${String(id).padStart(4, "0")}`;
}

function formatDate(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

function todayLabel() {
  return new Date().toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
}

function itemCell(item) {
  if (!item) return `<span class="item-sub">Unknown item</span>`;
  return `<div class="item-name">${escapeHtml(item.item_name)}</div>
    <div class="item-sub">${escapeHtml(item.department_category)}</div>`;
}

function initials(name) {
  return (name || "")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");
}

function nameParts(name) {
  const parts = (name || "").trim().split(/\s+/);
  const first = parts.shift() || "";
  return { first, last: parts.join(" ") };
}

function showNotice(el, type, message) {
  el.className = `notice show ${type}`;
  el.textContent = message;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function wireEyeToggles() {
  document.querySelectorAll("[data-eye]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const input = document.getElementById(btn.dataset.eye);
      input.type = input.type === "password" ? "text" : "password";
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  hydrateIcons();
  wireEyeToggles();
});
