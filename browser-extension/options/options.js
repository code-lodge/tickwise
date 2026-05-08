const browserAPI = (typeof browser !== "undefined") ? browser : chrome;

const $ = (id) => document.getElementById(id);

const DEFAULTS = {
  host: "127.0.0.1:19532",
  excludedDomains: ["mail.google.com", "online.banking"],
  captureSnippets: true,
};

function loadOptions() {
  return new Promise((resolve) => browserAPI.storage.local.get(DEFAULTS, resolve));
}

function saveOptions(opts) {
  return new Promise((resolve) => browserAPI.storage.local.set(opts, resolve));
}

function parseDomains(text) {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
}

async function init() {
  const opts = await loadOptions();
  $("host").value = opts.host;
  $("capture-snippets").checked = !!opts.captureSnippets;
  $("excluded").value = (opts.excludedDomains || []).join("\n");
}

$("btn-test").addEventListener("click", () => {
  const host = $("host").value || DEFAULTS.host;
  $("test-result").textContent = "Testing…";
  $("test-result").className = "";
  browserAPI.runtime.sendMessage({ type: "ping-host", host }, (resp) => {
    if (resp && resp.ok) {
      $("test-result").textContent = `Connected to Tickwise v${resp.status.version}`;
      $("test-result").className = "ok";
    } else {
      $("test-result").textContent = (resp && resp.error) || "Cannot reach host";
      $("test-result").className = "err";
    }
  });
});

$("btn-save").addEventListener("click", async () => {
  await saveOptions({
    host: $("host").value || DEFAULTS.host,
    captureSnippets: $("capture-snippets").checked,
    excludedDomains: parseDomains($("excluded").value),
  });
  $("save-result").textContent = "Saved.";
  $("save-result").className = "ok";
  setTimeout(() => ($("save-result").textContent = ""), 2000);
});

init();
