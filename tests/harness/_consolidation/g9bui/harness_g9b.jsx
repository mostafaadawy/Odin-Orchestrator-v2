// G9b UI test harness: the REAL ApprovalCenter with a mocked brain (no network).
import "./theme.css";
window.__posts = [];
const pending = [
  { id: "kkkk11112222", pid: "brand-three", member: "Email", title: "Key needed: KLAVIYO_KEY_BRAND3", kind: "key_request",
    key_service: "klaviyo", key_name: "KLAVIYO_KEY_BRAND3", severity: "routine", files: [], commands: [] },
];
window.fetch = async (url, opt = {}) => {
  const u = String(url);
  if ((opt.method || "GET") === "POST") {
    window.__posts.push({ url: u, body: opt.body ? JSON.parse(opt.body) : null });
    if (u.endsWith("/secrets/project-key")) {
      const b = JSON.parse(opt.body);
      pending.splice(0, pending.length);
      return new Response(JSON.stringify({ ok: true, id: b.aid, name: b.name, service: b.service }), { status: 200 });
    }
    return new Response(JSON.stringify({ ok: true }), { status: 200 });
  }
  if (u.includes("/approvals")) return new Response(JSON.stringify({ approvals: pending }), { status: 200 });
  return new Response("{}", { status: 200 });
};
import React from "react";
import { createRoot } from "react-dom/client";
import { ApprovalCenter } from "./views.jsx";
createRoot(document.getElementById("root")).render(<ApprovalCenter />);
