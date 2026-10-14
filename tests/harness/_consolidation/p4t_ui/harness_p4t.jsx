import React from "react";
import { createRoot } from "react-dom/client";
window.__srv = { mode: "normal", trained: true, posts: [], authority: "shadow" };
window.fetch = async (url, opts) => {
  const u = String(url);
  if (u.endsWith("/settings/decider-mode")) {
    if (opts && opts.method === "POST") {
      const b = JSON.parse(opts.body); window.__srv.posts.push(b.mode);
      if (b.mode === "jev" && !window.__srv.trained) return new Response(JSON.stringify({ detail: "not trained" }), { status: 409 });
      window.__srv.mode = b.mode; return new Response(JSON.stringify({ mode: b.mode, authority: window.__srv.authority }), { status: 200 });
    }
    return new Response(JSON.stringify({ mode: window.__srv.mode, authority: window.__srv.authority }), { status: 200 });
  }
  return new Response("{}", { status: 200 });
};
import("./App.jsx").then(({ DeciderToggle }) => {
  window.__mount = () => { const d = document.createElement("div"); d.id = "r" + Date.now(); document.body.appendChild(d); createRoot(d).render(<DeciderToggle />); };
  window.__mount();
});
