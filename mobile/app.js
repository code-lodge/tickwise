/* Tickwise mobile PWA — vanilla JS, no framework.
 *
 * Pairing flow: when the URL contains ?t=<token>, store the token in
 * localStorage and reload at the bare URL so the token is no longer
 * visible in the address bar.
 *
 * All authenticated requests include `Authorization: Bearer <token>`.
 */

const TOKEN_KEY = "tickwise.token";
const HOST_KEY = "tickwise.host";

const tabsEl = document.getElementById("tabs");
const appEl = document.getElementById("app");

// ─── Token + host bootstrap ─────────────────────────────────────────

(function bootstrapToken() {
  const params = new URLSearchParams(window.location.search);
  const t = params.get("t");
  if (t) {
    localStorage.setItem(TOKEN_KEY, t);
    // Use the same origin we were paired through.
    localStorage.setItem(HOST_KEY, window.location.origin);
    window.location.replace(window.location.pathname);
  }
})();

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function getHost() {
  return localStorage.getItem(HOST_KEY) || window.location.origin;
}

function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(HOST_KEY);
}

async function api(path, opts = {}) {
  const token = getToken();
  const headers = Object.assign({ "Content-Type": "application/json" }, opts.headers || {});
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${getHost()}/api/mobile${path}`, { ...opts, headers });
  if (res.status === 401) {
    clearToken();
    render();
    throw new Error("session expired — pair again");
  }
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      detail = (await res.json()).detail || detail;
    } catch (_) { /* ignore */ }
    throw new Error(detail);
  }
  return res.json();
}

// ─── Rendering helpers ──────────────────────────────────────────────

function fmtDuration(secs) {
  if (!secs) return "0m";
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  if (h) return `${h}h ${String(m).padStart(2, "0")}m`;
  return `${m}m`;
}

function fmtClock(secs) {
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function fmtTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function el(html) {
  const t = document.createElement("template");
  t.innerHTML = html.trim();
  return t.content.firstElementChild;
}

// ─── Screens ────────────────────────────────────────────────────────

function renderPairScreen() {
  appEl.innerHTML = "";
  appEl.appendChild(el(`
    <div class="pair-screen">
      <div class="logo">⏱️</div>
      <h1>Tickwise Mobile</h1>
      <p class="muted">Pair this device from the desktop dashboard:<br>
      <strong>Settings → Mobile → Pair Device</strong></p>
      <p class="muted" style="margin-top: 2rem;">Then scan the QR code or enter the token manually below.</p>
      <div style="margin-top: 1rem;">
        <input id="manual-token" type="text" placeholder="paste token here" autocomplete="off" autocapitalize="off">
      </div>
      <div style="margin-top: 1rem;">
        <input id="manual-host" type="text" placeholder="host (defaults to current origin)" autocomplete="off">
      </div>
      <div style="margin-top: 1rem;">
        <button class="primary" id="manual-save">Pair</button>
      </div>
      <div id="pair-error"></div>
    </div>
  `));
  document.getElementById("manual-save").addEventListener("click", () => {
    const token = document.getElementById("manual-token").value.trim();
    const host = document.getElementById("manual-host").value.trim();
    if (!token) {
      document.getElementById("pair-error").innerHTML =
        '<div class="error">Token is required.</div>';
      return;
    }
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(HOST_KEY, host || window.location.origin);
    render();
  });
}

let pollHandle = null;

async function renderHome() {
  appEl.innerHTML = '<div class="card"><span class="muted">Loading…</span></div>';
  try {
    const [today, status] = await Promise.all([api("/today"), api("/status")]);
    const projects = (today.by_project || []).map((p) => `
      <div class="session">
        <div class="dot" style="background:${p.color}"></div>
        <div class="session-meta"><div class="title">${p.name}</div></div>
        <div class="session-dur">${fmtDuration(p.seconds)}</div>
      </div>
    `).join("");
    appEl.innerHTML = `
      <h1>Today</h1>
      <div class="card">
        <div class="muted">Total tracked</div>
        <div class="kpi">${fmtDuration(today.total_seconds)}</div>
        <div class="muted" style="font-size:0.85rem">
          ${today.session_count} sessions · ${fmtDuration(today.billable_seconds)} billable
        </div>
      </div>
      <div class="card">
        <h2>By project</h2>
        ${projects || '<div class="muted">No tracked time yet.</div>'}
      </div>
      <div class="card">
        <h2>Status</h2>
        <div class="muted">Tracking: ${status.tracking ? "active" : "paused"}</div>
        <div class="muted">Pomodoro: ${status.pomodoro ? status.pomodoro.state : "n/a"}</div>
      </div>
    `;
  } catch (e) {
    appEl.innerHTML = `<div class="error">${e.message}</div>`;
  }
}

async function renderTimeline() {
  appEl.innerHTML = '<div class="card"><span class="muted">Loading…</span></div>';
  try {
    const sessions = await api("/timeline?days=2");
    const rows = sessions.map((s) => `
      <div class="session">
        <div class="dot" style="background:${s.project_color || "#9CA3AF"}"></div>
        <div class="session-meta">
          <div class="title">${s.project_name || "Unassigned"}</div>
          <div class="time">${fmtTime(s.started_at)} – ${fmtTime(s.ended_at)}</div>
        </div>
        <div class="session-dur">${fmtDuration(s.duration_secs)}</div>
      </div>
    `).join("");
    appEl.innerHTML = `
      <h1>Timeline</h1>
      <div class="card">${rows || '<div class="muted">No sessions in the last 2 days.</div>'}</div>
    `;
  } catch (e) {
    appEl.innerHTML = `<div class="error">${e.message}</div>`;
  }
}

let lastNotifiedState = null;

async function renderPomodoro() {
  appEl.innerHTML = `
    <h1>Pomodoro</h1>
    <div class="card" id="pomo-card" style="text-align:center">
      <span class="muted">Loading…</span>
    </div>
    <div class="card">
      <button class="primary" id="btn-focus">Start focus</button>
      <button class="primary ghost" id="btn-short" style="margin-top:0.5rem">Short break</button>
      <button class="primary ghost" id="btn-long" style="margin-top:0.5rem">Long break</button>
      <button class="primary danger" id="btn-stop" style="margin-top:0.5rem">Stop</button>
    </div>
  `;
  document.getElementById("btn-focus").onclick = () => callPomo("start", "focus");
  document.getElementById("btn-short").onclick = () => callPomo("start", "short_break");
  document.getElementById("btn-long").onclick = () => callPomo("start", "long_break");
  document.getElementById("btn-stop").onclick = () => callPomo("stop");
  refreshPomodoroCard();
}

async function callPomo(action, target) {
  try {
    const path = action === "start" ? `/pomodoro/start?target=${target}` : "/pomodoro/stop";
    const snap = await api(path, { method: "POST" });
    paintPomodoro(snap);
  } catch (e) {
    document.getElementById("pomo-card").innerHTML = `<div class="error">${e.message}</div>`;
  }
}

function paintPomodoro(snap) {
  const card = document.getElementById("pomo-card");
  if (!card) return;
  card.innerHTML = `
    <span class="state-pill ${snap.state}">${snap.state.replace("_", " ")}</span>
    <div class="timer-clock">${snap.state === "idle" ? "—" : fmtClock(snap.remaining_secs)}</div>
    <div class="muted">${snap.completed_focus_count} focus periods completed</div>
  `;
  // Web push fallback — fire a Notification when state transitions out of focus/break.
  if (lastNotifiedState && lastNotifiedState !== snap.state && snap.state === "idle") {
    if (window.Notification && Notification.permission === "granted") {
      new Notification("Tickwise", { body: `${lastNotifiedState.replace("_", " ")} period ended` });
    }
  }
  lastNotifiedState = snap.state;
}

async function refreshPomodoroCard() {
  try {
    const snap = await api("/pomodoro/status");
    paintPomodoro(snap);
  } catch (e) { /* leave previous render */ }
}

async function renderProjects() {
  appEl.innerHTML = '<div class="card"><span class="muted">Loading…</span></div>';
  try {
    const projects = await api("/projects");
    const rows = projects.map((p) => `
      <div class="session">
        <div class="dot" style="background:${p.color}"></div>
        <div class="session-meta">
          <div class="title">${p.name}</div>
          <div class="time">${p.hourly_rate ? `${p.hourly_rate} ${p.currency}/h` : "no rate"}</div>
        </div>
      </div>
    `).join("");
    appEl.innerHTML = `
      <h1>Projects</h1>
      <div class="card">${rows || '<div class="muted">No active projects.</div>'}</div>
      <button class="primary ghost" id="logout">Unpair this device</button>
    `;
    document.getElementById("logout").onclick = () => {
      clearToken();
      render();
    };
  } catch (e) {
    appEl.innerHTML = `<div class="error">${e.message}</div>`;
  }
}

// ─── Tab routing ────────────────────────────────────────────────────

let currentTab = "home";

function selectTab(tab) {
  currentTab = tab;
  Array.from(tabsEl.querySelectorAll("button")).forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === tab);
  });
  if (pollHandle) {
    clearInterval(pollHandle);
    pollHandle = null;
  }
  if (tab === "home") {
    renderHome();
    pollHandle = setInterval(renderHome, 5000);
  } else if (tab === "timeline") renderTimeline();
  else if (tab === "pomodoro") {
    renderPomodoro();
    pollHandle = setInterval(refreshPomodoroCard, 1000);
  } else if (tab === "projects") renderProjects();
}

tabsEl.addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-tab]");
  if (btn) selectTab(btn.dataset.tab);
});

function render() {
  if (!getToken()) {
    if (pollHandle) clearInterval(pollHandle);
    tabsEl.style.display = "none";
    renderPairScreen();
    return;
  }
  tabsEl.style.display = "grid";
  selectTab(currentTab);
  if ("Notification" in window && Notification.permission === "default") {
    Notification.requestPermission();
  }
}

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("service-worker.js").catch(() => { /* ignore */ });
}

render();
