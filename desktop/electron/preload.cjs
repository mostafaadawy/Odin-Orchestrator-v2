// Safe bridge: lets the React UI open a native folder picker (any location on disk).
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("odin", {
  pickFolder: () => ipcRenderer.invoke("pick-folder"),
  pickFolders: () => ipcRenderer.invoke("pick-folders"),
  pickFiles: () => ipcRenderer.invoke("pick-files"),
  // Start the local REQUEST page (static server) and open it in the browser.
  startRequestPage: () => ipcRenderer.invoke("start-request-page"),
  // F-14: read an owner secret (allow-listed names) from the Keychain via the main process.
  secret: (name) => ipcRenderer.invoke("secret-get", name),
  // v2 Paper tab (catalog ids only)
  paperList: () => ipcRenderer.invoke("paper-list"),
  paperRead: (id) => ipcRenderer.invoke("paper-read", id),
  paperSave: (id) => ipcRenderer.invoke("paper-save", id),
  paperSaveGroup: (g) => ipcRenderer.invoke("paper-save-group", g),
  isDesktop: true,
});
