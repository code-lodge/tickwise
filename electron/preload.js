/* Tickwise — Electron preload.
 *
 * The dashboard is a regular FastAPI-served Angular app, so it doesn't
 * actually need an `electronAPI` bridge to function. We expose a tiny
 * read-only flag for any future code that wants to detect whether
 * it's running inside the Electron shell vs a plain browser tab.
 */

const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("tickwise", {
  isElectron: true,
  platform: process.platform,
});
