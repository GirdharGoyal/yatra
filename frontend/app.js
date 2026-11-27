const API_BASE = "http://127.0.0.1:8000";

function getToken() {
  return localStorage.getItem("yatra_token");
}

function setToken(token) {
  localStorage.setItem("yatra_token", token);
}

function logout() {
  localStorage.removeItem("yatra_token");
  window.location.href = "login.html";
}

async function apiFetch(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `Error ${res.status}`);
  }
  return data;
}

async function renderNavbar() {
  const nav = document.getElementById("navbar");
  if (!nav) return;

  let authHtml = `<a href="login.html">Login / Signup</a>`;
  if (getToken()) {
    try {
      const user = await apiFetch("/me");
      authHtml = `
        <span>Hi, <strong>${user.name || user.email}</strong></span>
        <button class="btn-outline" onclick="logout()">Logout</button>
      `;
    } catch {
      localStorage.removeItem("yatra_token");
    }
  }

  nav.innerHTML = `
    <a href="index.html" class="logo">Yatra<span>.ai</span></a>
    <div class="nav-links">
      <a href="search.html">Explore</a>
      <a href="bookings.html">My Bookings</a>
      ${authHtml}
    </div>
  `;
}

document.addEventListener("DOMContentLoaded", renderNavbar);
