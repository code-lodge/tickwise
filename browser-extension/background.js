/* Tickwise browser bridge — service worker / background script.
 *
 * Watches the active tab and pushes URL + title (+ optional snippet) to
 * the Tickwise desktop app over WebSocket. The user can exclude
 * domains and disable content snippets in the options page; both rules
 * apply on the extension side so no excluded data ever leaves the
 * browser.
 *
 * Single source of truth for cross-browser compat:
 *   - Manifest V3 (Chrome) treats this as a service worker.
 *   - Manifest V2 (Firefox) treats this as a persistent background page.
 *   - Both expose `chrome.*` (or `browser.*` polyfilled below).
 */

const browserAPI = (typeof browser !== "undefined") ? browser : chrome;

const DEFAULT_HOST = "127.0.0.1:19532";
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30_000;
const SEND_DEBOUNCE_MS = 250;

let socket = null;
let reconnectAttempts = 0;
let reconnectTimer = null;
let pendingSendTimer = null;
let lastPayload = null;
let connectionState = "disconnected";

function loadOptions() {
  return new Promise((resolve) => {
    browserAPI.storage.local.get(
      {
        host: DEFAULT_HOST,
        excludedDomains: ["mail.google.com", "online.banking"],
        captureSnippets: true,
      },
      (items) => resolve(items),
    );
  });
}

function isExcluded(url, excludedDomains) {
  if (!url) return true;
  let parsed;
  try {
    parsed = new URL(url);
  } catch (_) {
    return true;
  }
  if (!/^https?:$/.test(parsed.protocol)) return true;
  return excludedDomains.some((d) => {
    if (!d) return false;
    return parsed.hostname === d || parsed.hostname.endsWith("." + d);
  });
}

function setConnectionState(state) {
  connectionState = state;
  browserAPI.storage.local.set({ connectionState: state });
}

async function ensureSocket() {
  if (socket && (socket.readyState === 0 || socket.readyState === 1)) return;
  const { host } = await loadOptions();
  const url = `ws://${host}/ws/browser-extension`;
  setConnectionState("connecting");
  try {
    socket = new WebSocket(url);
  } catch (e) {
    scheduleReconnect();
    return;
  }
  socket.onopen = () => {
    reconnectAttempts = 0;
    setConnectionState("connected");
  };
  socket.onmessage = (evt) => {
    let msg;
    try {
      msg = JSON.parse(evt.data);
    } catch (_) {
      return;
    }
    if (msg.type === "pong" || msg.type === "connected") return;
  };
  socket.onclose = () => {
    setConnectionState("disconnected");
    scheduleReconnect();
  };
  socket.onerror = () => {
    setConnectionState("error");
  };
}

function scheduleReconnect() {
  if (reconnectTimer) return;
  const delay = Math.min(RECONNECT_BASE_MS * 2 ** reconnectAttempts, RECONNECT_MAX_MS);
  reconnectAttempts += 1;
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    ensureSocket();
  }, delay);
}

function send(payload) {
  if (!socket || socket.readyState !== 1) return;
  try {
    socket.send(JSON.stringify(payload));
    lastPayload = payload;
  } catch (e) {
    setConnectionState("error");
  }
}

async function pushTabContext(tab) {
  if (!tab || !tab.url) return;
  const opts = await loadOptions();
  if (isExcluded(tab.url, opts.excludedDomains)) return;
  const payload = {
    type: "context",
    url: tab.url,
    title: tab.title || "",
    content_snippet: null,
  };
  if (opts.captureSnippets) {
    try {
      const [{ result } = {}] = await browserAPI.scripting.executeScript({
        target: { tabId: tab.id },
        func: () => {
          const text = document.body ? document.body.innerText : "";
          return text.slice(0, 1500);
        },
      });
      payload.content_snippet = result || null;
    } catch (_) {
      // Some pages (chrome://, store pages) refuse script injection.
    }
  }
  if (pendingSendTimer) clearTimeout(pendingSendTimer);
  pendingSendTimer = setTimeout(() => {
    pendingSendTimer = null;
    send(payload);
    browserAPI.storage.local.set({
      lastUrl: payload.url,
      lastTitle: payload.title,
    });
  }, SEND_DEBOUNCE_MS);
}

async function activeTab() {
  return new Promise((resolve) => {
    browserAPI.tabs.query({ active: true, lastFocusedWindow: true }, (tabs) =>
      resolve(tabs && tabs[0]),
    );
  });
}

browserAPI.tabs.onActivated.addListener(async (activeInfo) => {
  await ensureSocket();
  browserAPI.tabs.get(activeInfo.tabId, (tab) => pushTabContext(tab));
});

browserAPI.tabs.onUpdated.addListener(async (_tabId, changeInfo, tab) => {
  if (!tab.active) return;
  if (!changeInfo.url && !changeInfo.title && changeInfo.status !== "complete") return;
  await ensureSocket();
  pushTabContext(tab);
});

browserAPI.windows.onFocusChanged.addListener(async (windowId) => {
  if (windowId === browserAPI.windows.WINDOW_ID_NONE) return;
  await ensureSocket();
  const tab = await activeTab();
  pushTabContext(tab);
});

browserAPI.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg && msg.type === "ping-host") {
    fetch(`http://${(msg.host || DEFAULT_HOST)}/api/status`)
      .then((r) => r.json())
      .then((j) => sendResponse({ ok: true, status: j }))
      .catch((e) => sendResponse({ ok: false, error: String(e) }));
    return true; // keep channel open for async response
  }
  if (msg && msg.type === "pomodoro-action") {
    fetch(
      `http://${(msg.host || DEFAULT_HOST)}/api/pomodoro/${msg.action}` +
        (msg.target ? `?target=${msg.target}` : ""),
      { method: "POST" },
    )
      .then((r) => r.json())
      .then((j) => sendResponse({ ok: true, status: j }))
      .catch((e) => sendResponse({ ok: false, error: String(e) }));
    return true;
  }
  if (msg && msg.type === "get-state") {
    loadOptions().then((opts) => {
      sendResponse({
        connectionState,
        lastPayload,
        host: opts.host,
        excludedDomains: opts.excludedDomains,
        captureSnippets: opts.captureSnippets,
      });
    });
    return true;
  }
  return false;
});

ensureSocket();
