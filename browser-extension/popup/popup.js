const browserAPI = (typeof browser !== "undefined") ? browser : chrome;

const $ = (id) => document.getElementById(id);

function fmt(secs) {
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function applyState(snapshot) {
  const stateEl = $("pomo-state");
  stateEl.textContent = snapshot.state.replace("_", " ");
  stateEl.className = "state " + snapshot.state;
  $("pomo-remaining").textContent = snapshot.state === "idle" ? "—" : fmt(snapshot.remaining_secs);
}

async function refreshHostState() {
  browserAPI.runtime.sendMessage({ type: "get-state" }, (resp) => {
    if (!resp) return;
    const conn = $("connection-state");
    conn.textContent = resp.connectionState || "disconnected";
    conn.className = "state " + (resp.connectionState || "disconnected");
    if (resp.lastPayload) {
      $("last-title").textContent = resp.lastPayload.title || "—";
      $("last-url").textContent = resp.lastPayload.url || "—";
    }
    fetch(`http://${resp.host}/api/pomodoro/status`)
      .then((r) => r.json())
      .then(applyState)
      .catch((e) => ($("error").textContent = String(e)));
  });
}

$("btn-focus").addEventListener("click", () => {
  browserAPI.runtime.sendMessage(
    { type: "pomodoro-action", action: "start", target: "focus" },
    (resp) => {
      if (resp && resp.ok) applyState(resp.status);
      else $("error").textContent = (resp && resp.error) || "failed";
    },
  );
});

$("btn-stop").addEventListener("click", () => {
  browserAPI.runtime.sendMessage({ type: "pomodoro-action", action: "stop" }, (resp) => {
    if (resp && resp.ok) applyState(resp.status);
    else $("error").textContent = (resp && resp.error) || "failed";
  });
});

$("open-options").addEventListener("click", (e) => {
  e.preventDefault();
  if (browserAPI.runtime.openOptionsPage) browserAPI.runtime.openOptionsPage();
});

refreshHostState();
setInterval(refreshHostState, 1000);
