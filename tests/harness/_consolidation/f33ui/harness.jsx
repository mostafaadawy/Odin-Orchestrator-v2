// F-33 UI test harness: renders the REAL ApprovalCenter with a mocked brain (no network).
import "./theme.css";
window.__posts = [];
const pending = [
  { id: "aaaa11112222", pid: "shop-site", member: "Fullstack", title: "Add contact form", severity: "routine",
    files: [{ path: "workspace/projects/shop-site/code/form.html", action: "create" }], commands: [] },
  { id: "bbbb33334444", pid: "crm-sync", member: "DevOps", title: "Install deps", severity: "caution",
    files: [], commands: [{ cmd: "npm ci", where: "local" }] },
  { id: "ssss55556666", pid: "vm-sentinel", member: "SecCTO", title: "Block IP", security: true, severity: "security",
    files: [], commands: [{ cmd: "ufw deny from 1.2.3.4", where: "vm" }] },
];
window.fetch = async (url, opt = {}) => {
  const u = String(url);
  if ((opt.method || "GET") === "POST") {
    window.__posts.push(u);
    const id = (u.match(/approvals\/([0-9a-z]+)\/approve/) || [])[1];
    const i = pending.findIndex((p) => p.id === id); if (i >= 0) pending.splice(i, 1);
    return new Response(JSON.stringify({ ok: true }), { status: 200 });
  }
  if (u.includes("/approvals")) return new Response(JSON.stringify({ approvals: pending }), { status: 200 });
  return new Response("{}", { status: 200 });
};
import React from "react";
import { createRoot } from "react-dom/client";
import { ApprovalCenter } from "./views.jsx";
createRoot(document.getElementById("root")).render(<ApprovalCenter />);
