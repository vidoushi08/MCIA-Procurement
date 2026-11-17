const API_BASE = "http://127.0.0.1:8000";

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });

  let body = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }

  if (!response.ok) {
    const detail = body && body.detail;
    let message = `Request failed (${response.status})`;
    if (typeof detail === "string") {
      message = detail;
    } else if (Array.isArray(detail) && detail.length) {
      message = detail.map((d) => d.msg).join("; ");
    }
    throw new Error(message);
  }

  return body;
}

const api = {
  get: (path) => apiRequest(path),
  post: (path, data) => apiRequest(path, { method: "POST", body: JSON.stringify(data) }),
};

const session = {
  set(staffId) {
    sessionStorage.setItem("mcia.staffId", String(staffId));
  },
  get() {
    return sessionStorage.getItem("mcia.staffId");
  },
  clear() {
    sessionStorage.removeItem("mcia.staffId");
  },
};
