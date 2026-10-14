import React from "react";
import { motion, AnimatePresence } from "framer-motion";

// ---- agent avatar with role identity + live heartbeat (Phase 3) ----
const ROLE = {
  cto: { c: "var(--brand-2)", g: "🧭", label: "CTO" },
  frontend: { c: "var(--frontend)", g: "▦", label: "FE" },
  backend: { c: "var(--backend)", g: "❮❯", label: "BE" },
  devops: { c: "var(--devops)", g: "☁", label: "OPS" },
  security: { c: "var(--security)", g: "⛨", label: "SEC" },
  qa: { c: "var(--qa)", g: "✓", label: "QA" },
  database: { c: "var(--database)", g: "▤", label: "DB" },
  generic: { c: "var(--generic)", g: "✦", label: "AI" },
};
export function avatarKey(a) {
  const k = (a || "generic").toLowerCase();
  return ROLE[k] ? k : "generic";
}
export function Avatar({ kind = "generic", active = false, size = "" , initials }) {
  const r = ROLE[avatarKey(kind)];
  return (
    <div className={`avatar ${size} ${active ? "active" : ""}`} style={{ color: r.c }}>
      <span className="heart-ring" />
      <div className="glyph" style={{ background: `linear-gradient(160deg, ${r.c}, color-mix(in srgb, ${r.c} 55%, #0a0c12))` }}>
        {initials || r.g}
      </div>
    </div>
  );
}

export function StatusDot({ state = "ok", label }) {
  const cls = state === true || state === "ok" ? "ok" : state === "warn" ? "warn" : "bad";
  return (
    <span className="row" style={{ gap: 7 }}>
      <span className={`dot ${cls}`} />
      {label && <span className="muted" style={{ fontSize: 12.5 }}>{label}</span>}
    </span>
  );
}

export function Modal({ open, onClose, title, children, footer }) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div className="overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose}>
          <motion.div
            className="card pad modal"
            initial={{ scale: 0.94, y: 14, opacity: 0 }}
            animate={{ scale: 1, y: 0, opacity: 1 }}
            exit={{ scale: 0.96, opacity: 0 }}
            transition={{ type: "spring", stiffness: 320, damping: 26 }}
            onClick={(e) => e.stopPropagation()}
            style={{ display: "flex", flexDirection: "column", maxHeight: "86vh" }}
          >
            <div className="row between" style={{ marginBottom: 14, flexShrink: 0 }}>
              <h3 className="h-title">{title}</h3>
              <button className="iconbtn" onClick={onClose} style={{ width: 34, height: 34 }}>✕</button>
            </div>
            {/* body scrolls so the footer buttons are ALWAYS reachable no matter how tall the content */}
            <div className="col" style={{ overflowY: "auto", flex: "1 1 auto", minHeight: 0 }}>{children}</div>
            {footer && <div className="row between" style={{ marginTop: 18, flexShrink: 0 }}>{footer}</div>}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export function UsageBar({ percent, color }) {
  return (
    <div className="bar">
      <motion.span
        style={{ background: color }}
        initial={{ width: 0 }}
        animate={{ width: `${Math.max(2, percent)}%` }}
        transition={{ duration: 0.6 }}
      />
    </div>
  );
}

// ---- lightweight markdown -> HTML (tables, bold, code, lists, headers) ----
export function renderMarkdown(raw) {
  if (!raw) return "";
  const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const lines = raw.replace(/\r/g, "").split("\n");
  let html = "", i = 0;
  const inline = (t) =>
    esc(t)
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>");
  while (i < lines.length) {
    const L = lines[i];
    if (L.trim().startsWith("```")) {
      let code = ""; i++;
      while (i < lines.length && !lines[i].trim().startsWith("```")) { code += lines[i] + "\n"; i++; }
      i++; html += `<pre><code>${esc(code)}</code></pre>`; continue;
    }
    if (/^\s*\|.*\|\s*$/.test(L) && i + 1 < lines.length && /^\s*\|[-:\s|]+\|\s*$/.test(lines[i + 1])) {
      const head = L.split("|").slice(1, -1).map((s) => s.trim());
      i += 2; let rows = [];
      while (i < lines.length && /^\s*\|.*\|\s*$/.test(lines[i])) {
        rows.push(lines[i].split("|").slice(1, -1).map((s) => s.trim())); i++;
      }
      html += "<table><thead><tr>" + head.map((h) => `<th>${inline(h)}</th>`).join("") + "</tr></thead><tbody>" +
        rows.map((r) => "<tr>" + r.map((c) => `<td>${inline(c)}</td>`).join("") + "</tr>").join("") + "</tbody></table>";
      continue;
    }
    const h = L.match(/^(#{1,4})\s+(.*)$/);
    if (h) { html += `<h${h[1].length + 2}>${inline(h[2])}</h${h[1].length + 2}>`; i++; continue; }
    if (/^\s*[-*]\s+/.test(L)) {
      let items = [];
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) { items.push(lines[i].replace(/^\s*[-*]\s+/, "")); i++; }
      html += "<ul>" + items.map((t) => `<li>${inline(t)}</li>`).join("") + "</ul>"; continue;
    }
    if (L.trim() === "") { html += ""; i++; continue; }
    html += `<p>${inline(L)}</p>`; i++;
  }
  return html;
}

// strip markdown/code so TTS reads clean prose
export function toSpeech(raw) {
  if (!raw) return "";
  return raw
    .replace(/```[\s\S]*?```/g, " code block. ")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\|/g, " ")
    .replace(/[#*_>]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

export function Markdown({ text }) {
  return <div dangerouslySetInnerHTML={{ __html: renderMarkdown(text) }} />;
}
