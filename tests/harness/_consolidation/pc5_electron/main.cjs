const { app, BrowserWindow, protocol, net } = require("electron");
const path = require("path");
const { DESKTOP_ORIGIN, registerScheme, serveDist } = require("./appProtocol.cjs");
registerScheme(protocol);
app.whenReady().then(async () => {
  serveDist(protocol, net, path.join(__dirname, "dist"));
  const w = new BrowserWindow({ show: false, webPreferences: { contextIsolation: true, nodeIntegration: false } });
  await w.loadURL(DESKTOP_ORIGIN + "/index.html");
  const r = await w.webContents.executeJavaScript("window.runTests()");
  const trav = await w.webContents.executeJavaScript("fetch('app://odin-desktop/../../etc/passwd').then(r=>r.status).catch(e=>'ERR')");
  console.log("RESULT " + JSON.stringify({ ...r, traversal: trav }));
  app.quit();
});
