const PORTAL_HOME = {
  STAFF: "../staff/dashboard.html",
  DEPT_HEAD: "../dept-head/dashboard.html",
  ADMIN: "../admin/dashboard.html",
};

function roleHome(role) {
  return PORTAL_HOME[role] || "../index.html";
}

function money(value) {
  return `Rs ${Number(value).toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function flash(type, message) {
  const notice = document.getElementById("notice");
  if (notice) showNotice(notice, type, message);
}

function setBody(body, html) {
  body.innerHTML = html;
  hydrateIcons(body);
}

function pageHead(title, description, actions = "") {
  return `<div class="page-head">
    <div><h1>${escapeHtml(title)}</h1><p>${escapeHtml(description)}</p></div>
    ${actions}
  </div>`;
}

function statCard(label, value, note, icon = "list") {
  return `<div class="card stat">
    <div class="stat-top">${escapeHtml(label)} <span data-icon="${icon}"></span></div>
    <div class="stat-num">${escapeHtml(String(value))}</div>
    <div class="stat-note">${escapeHtml(note)}</div>
  </div>`;
}

function dataTable(headers, rowsHtml, emptyText) {
  const body = rowsHtml || `<tr><td class="empty-cell" colspan="${headers.length}">${escapeHtml(emptyText)}</td></tr>`;
  return `<div class="card table-card"><table>
    <thead><tr>${headers.map((h) => `<th>${escapeHtml(h)}</th>`).join("")}</tr></thead>
    <tbody>${body}</tbody>
  </table></div>`;
}

function formCard(title, fields, submitLabel, formId) {
  return `<div class="card card-body" style="margin-bottom:36px">
    <h2 class="section-title" style="font-size:17px;margin-bottom:18px">${escapeHtml(title)}</h2>
    <form id="${formId}" novalidate>
      <div class="form-row split">${fields}</div>
      <div style="margin-top:18px"><button class="btn btn-primary" type="submit">${escapeHtml(submitLabel)}</button></div>
    </form>
  </div>`;
}

function field(id, label, control) {
  return `<div class="field"><label for="${id}">${escapeHtml(label)}</label>${control}</div>`;
}

function textInput(id, opts = {}) {
  const attrs = [
    `type="${opts.type || "text"}"`,
    opts.required ? "required" : "",
    opts.min !== undefined ? `min="${opts.min}"` : "",
    opts.step ? `step="${opts.step}"` : "",
    opts.minlength ? `minlength="${opts.minlength}"` : "",
    opts.placeholder ? `placeholder="${escapeHtml(opts.placeholder)}"` : "",
  ].join(" ");
  return `<input class="input" id="${id}" ${attrs}>`;
}

function selectInput(id, options) {
  const opts = options.map(([value, label]) => `<option value="${escapeHtml(value)}">${escapeHtml(label)}</option>`).join("");
  return `<select class="input" id="${id}">${opts}</select>`;
}

function onFormSubmit(form, handler, reload) {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    try {
      const message = await handler(new FormData(form));
      await reload();
      flash("success", message);
    } catch (error) {
      flash("error", error.message);
    } finally {
      submitBtn.disabled = false;
    }
  });
}

function wireActions(container, handlers, reload) {
  container.querySelectorAll("[data-act]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      try {
        const message = await handlers[btn.dataset.act](btn);
        await reload();
        flash("success", message);
      } catch (error) {
        flash("error", error.message);
      }
    });
  });
}

function shortDate(iso) {
  return iso ? formatDate(iso) : "";
}
