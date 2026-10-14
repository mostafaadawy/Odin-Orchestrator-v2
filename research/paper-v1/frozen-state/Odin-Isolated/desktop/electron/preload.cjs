// Safe bridge: lets the React UI open a native folder picker (any location on disk).
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("odin", {
  pickFolder: () => ipcRenderer.invoke("pick-folder"),
  pickFolders: () => ipcRenderer.invoke("pick-folders"),
  pickFiles: () => ipcRenderer.invoke("pick-files"),
  // Start the local REQUEST page (static server) and open it in the browser.
  startRequestPage: () => ipcRenderer.invoke("start-request-page"),
  isDesktop: true,
});
