/* Content script — minimal. The background script does most of the
 * work via chrome.scripting.executeScript, but having a stub content
 * script satisfies Firefox's MV2 model where some hosts only allow
 * messaging from declared content scripts. We forward the page's
 * innerText to the background on demand.
 */

const browserAPI = (typeof browser !== "undefined") ? browser : chrome;

browserAPI.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg && msg.type === "extract-text") {
    sendResponse({ snippet: (document.body ? document.body.innerText : "").slice(0, 1500) });
    return true;
  }
  return false;
});
