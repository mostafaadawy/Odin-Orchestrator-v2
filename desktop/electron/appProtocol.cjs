// PC-5 (owner 2026-10-12): the desktop UI is served from its OWN origin, app://odin-desktop — not file://, whose
// origin is "null" and cannot be told apart from a sandboxed web page. The brain allows only this origin and
// localhost; every other web origin is refused for reads and writes.
const path = require("path");
const { pathToFileURL } = require("url");

const DESKTOP_ORIGIN = "app://odin-desktop";

function registerScheme(protocol) {   // must run before app 'ready'
  protocol.registerSchemesAsPrivileged([{ scheme: "app", privileges: { standard: true, secure: true, supportFetchAPI: true, corsEnabled: true } }]);
}

function serveDist(protocol, net, distDir) {
  const root = path.resolve(distDir);
  protocol.handle("app", (req) => {
    const u = new URL(req.url);
    if (u.host !== "odin-desktop") return new Response("not found", { status: 404 });
    let p = decodeURIComponent(u.pathname);
    if (!p || p === "/") p = "/index.html";
    const f = path.resolve(path.join(root, p));
    if (f !== root && !f.startsWith(root + path.sep)) return new Response("forbidden", { status: 403 });
    return net.fetch(pathToFileURL(f).toString());
  });
}

module.exports = { DESKTOP_ORIGIN, registerScheme, serveDist };
