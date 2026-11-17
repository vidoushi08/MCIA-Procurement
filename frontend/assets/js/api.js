const API_BASE = "http://127.0.0.1:8000";

async function apiRequest(path, options = {}) {
  const token = session.token();
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });

  let body = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }

  if (response.status === 401 && token) {
    session.clear();
    const inSubfolder = /\/(staff|admin|dept-head)\//.test(location.pathname);
    location.href = inSubfolder ? "../index.html" : "index.html";
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
  put: (path, data) => apiRequest(path, { method: "PUT", body: data === undefined ? undefined : JSON.stringify(data) }),
};

const session = {
  set(token, user) {
    sessionStorage.setItem("mcia.token", token);
    sessionStorage.setItem("mcia.user", JSON.stringify(user));
  },
  token() {
    return sessionStorage.getItem("mcia.token");
  },
  user() {
    const raw = sessionStorage.getItem("mcia.user");
    return raw ? JSON.parse(raw) : null;
  },
  clear() {
    sessionStorage.removeItem("mcia.token");
    sessionStorage.removeItem("mcia.user");
  },
};
