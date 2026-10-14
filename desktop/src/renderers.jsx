// v2 Paper tab: show each file the way its type is meant to be read (no raw text):
// .md → formatted document · .tex → typeset-style document, tables as real tables · .json → readable tree ·
// .jsonl / .csv → tables · .bib → reference list · code (.py …) → code view with line numbers.
// No external libraries; every input is HTML-escaped before formatting.
import React, { useState } from "react";

const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

// ---------------------------------------------------------------- Markdown
function mdInline(s) {
  return esc(s)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>")
    .replace(/(^|[^*])\*([^*\s][^*]*)\*/g, "$1<i>$2</i>")
    .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>');
}
function mdToHtml(src) {
  const L = src.replace(/\r/g, "").split("\n"); const out = []; let i = 0;
  while (i < L.length) {
    const l = L[i];
    if (/^```/.test(l)) { const b = []; i++; while (i < L.length && !/^```/.test(L[i])) b.push(esc(L[i++])); i++; out.push("<pre class='r-code'>" + b.join("\n") + "</pre>"); continue; }
    const h = l.match(/^(#{1,6})\s+(.*)/); if (h) { out.push(`<h${h[1].length}>${mdInline(h[2])}</h${h[1].length}>`); i++; continue; }
    if (/^\s*(---|\*\*\*)\s*$/.test(l)) { out.push("<hr/>"); i++; continue; }
    if (/^\s*\|.*\|\s*$/.test(l) && i + 1 < L.length && /^\s*\|?\s*:?-{2,}/.test(L[i + 1])) {
      const cells = (x) => x.trim().replace(/^\||\|$/g, "").split("|").map((c) => mdInline(c.trim()));
      const head = cells(l); i += 2; const rows = [];
      while (i < L.length && /^\s*\|.*\|\s*$/.test(L[i])) rows.push(cells(L[i++]));
      out.push("<table class='r-table'><thead><tr>" + head.map((c) => `<th>${c}</th>`).join("") + "</tr></thead><tbody>" +
        rows.map((r) => "<tr>" + r.map((c) => `<td>${c}</td>`).join("") + "</tr>").join("") + "</tbody></table>"); continue;
    }
    if (/^\s*([-*+]|\d+\.)\s+/.test(l)) {
      const ord = /^\s*\d+\./.test(l); const items = [];
      while (i < L.length && /^\s*([-*+]|\d+\.)\s+/.test(L[i])) items.push("<li>" + mdInline(L[i++].replace(/^\s*([-*+]|\d+\.)\s+/, "")) + "</li>");
      out.push((ord ? "<ol>" : "<ul>") + items.join("") + (ord ? "</ol>" : "</ul>")); continue;
    }
    if (/^>\s?/.test(l)) { const q = []; while (i < L.length && /^>\s?/.test(L[i])) q.push(mdInline(L[i++].replace(/^>\s?/, ""))); out.push("<blockquote>" + q.join("<br/>") + "</blockquote>"); continue; }
    if (!l.trim()) { i++; continue; }
    const p = []; while (i < L.length && L[i].trim() && !/^(#|```|\s*([-*+]|\d+\.)\s|\s*\|)/.test(L[i])) p.push(mdInline(L[i++]));
    out.push("<p>" + p.join(" ") + "</p>");
  }
  return out.join("\n");
}

// ---------------------------------------------------------------- LaTeX
function texInline(s) {
  let t = esc(s);
  t = t.replace(/\\%/g, "%").replace(/\\&amp;/g, "&amp;").replace(/\\_/g, "_").replace(/\\#/g, "#").replace(/\\\$/g, "$")
    .replace(/---/g, "—").replace(/--/g, "–").replace(/``|''/g, "\"").replace(/~/g, " ").replace(/\\ /g, " ").replace(/\\,/g, " ");
  for (let k = 0; k < 3; k++) {
    t = t.replace(/\\textbf\{([^{}]*)\}/g, "<b>$1</b>").replace(/\\(emph|textit)\{([^{}]*)\}/g, "<i>$2</i>")
      .replace(/\\texttt\{([^{}]*)\}/g, "<code>$1</code>").replace(/\\url\{([^{}]*)\}/g, "<code>$1</code>")
      .replace(/\\(cite|citep|citet)\{([^{}]*)\}/g, "<span class='r-cite'>[$2]</span>")
      .replace(/\\(ref|autoref|cref|Cref)\{([^{}]*)\}/g, "<span class='r-cite'>$2</span>")
      .replace(/\\(label)\{[^{}]*\}/g, "").replace(/\\(footnote)\{([^{}]*)\}/g, " <span class='r-cite'>($2)</span>")
      .replace(/\\(mathrm|text|mathit|mathbf)\{([^{}]*)\}/g, "$2");
  }
  t = t.replace(/\$([^$]+)\$/g, (_, m) => "<i>" + m.replace(/\\(le|leq)\b/g, "≤").replace(/\\(ge|geq)\b/g, "≥").replace(/\\times/g, "×")
    .replace(/\\pm/g, "±").replace(/\\approx/g, "≈").replace(/\\alpha/g, "α").replace(/\\tau/g, "τ").replace(/\\to/g, "→")
    .replace(/\^\{?([^}\s]+)\}?/g, "<sup>$1</sup>").replace(/_\{?([^}\s]+)\}?/g, "<sub>$1</sub>").replace(/\\[a-zA-Z]+/g, "") + "</i>");
  return t.replace(/\\(toprule|midrule|bottomrule|hline|centering|small|scriptsize|footnotesize|noindent|par|newline)\b/g, "").replace(/\\\\/g, "<br/>");
}
function tabularToHtml(body) {
  const rows = body.replace(/\\(toprule|midrule|bottomrule|hline|cmidrule(\([^)]*\))?\{[^}]*\})/g, "\n").split(/\\\\/).map((r) => r.trim()).filter(Boolean);
  if (!rows.length) return "";
  const cells = (r) => r.split(/(?<!\\)&/).map((c) => texInline(c.trim().replace(/\\multicolumn\{\d+\}\{[^}]*\}\{([^}]*)\}/g, "$1")));
  return "<table class='r-table'><thead><tr>" + cells(rows[0]).map((c) => `<th>${c}</th>`).join("") + "</tr></thead><tbody>" +
    rows.slice(1).map((r) => "<tr>" + cells(r).map((c) => `<td>${c}</td>`).join("") + "</tr>").join("") + "</tbody></table>";
}
function texToHtml(src) {
  let s = src.replace(/(^|[^\\])%.*$/gm, "$1");                      // comments
  s = s.replace(/\\documentclass[\s\S]*?\\begin\{document\}/, "").replace(/\\end\{document\}/, "");
  const blocks = [];
  s = s.replace(/\\begin\{tabular\*?\}(\{[^}]*\})?\{[^}]*\}([\s\S]*?)\\end\{tabular\*?\}/g, (_, _w, b) => { blocks.push(tabularToHtml(b)); return `@@B${blocks.length - 1}@@`; });
  s = s.replace(/\\caption\{((?:[^{}]|\{[^{}]*\})*)\}/g, (_, c) => { blocks.push("<div class='r-caption'>" + texInline(c) + "</div>"); return `@@B${blocks.length - 1}@@`; });
  s = s.replace(/\\begin\{(table|figure)\*?\}(\[[^\]]*\])?/g, "<div class='r-float'>").replace(/\\end\{(table|figure)\*?\}/g, "</div>");
  s = s.replace(/\\includegraphics(\[[^\]]*\])?\{([^}]*)\}/g, (_, _o, f) => `<div class='r-note'>[figure: ${esc(f)}]</div>`);
  s = s.replace(/\\input\{([^}]*)\}/g, (_, f) => `<div class='r-note'>[includes ${esc(f)}.tex — open it in the list to see it]</div>`);
  s = s.replace(/\\begin\{(itemize|enumerate)\}([\s\S]*?)\\end\{\1\}/g, (_, k, b) =>
    (k === "enumerate" ? "<ol>" : "<ul>") + b.split(/\\item/).slice(1).map((x) => "<li>" + texInline(x.trim()) + "</li>").join("") + (k === "enumerate" ? "</ol>" : "</ul>"));
  s = s.replace(/\\begin\{abstract\}([\s\S]*?)\\end\{abstract\}/g, (_, a) => "<div class='r-abstract'><b>Abstract.</b> " + texInline(a) + "</div>");
  s = s.replace(/\\title\{([^}]*)\}/g, (_, t) => "<h1>" + texInline(t) + "</h1>").replace(/\\(section)\*?\{([^}]*)\}/g, (_, _k, t) => "\n<h2>" + texInline(t) + "</h2>\n")
    .replace(/\\subsection\*?\{([^}]*)\}/g, (_, t) => "\n<h3>" + texInline(t) + "</h3>\n").replace(/\\(subsubsection|paragraph)\*?\{([^}]*)\}/g, (_, _k, t) => "\n<h4>" + texInline(t) + "</h4>\n");
  s = s.replace(/\\(maketitle|bibliographystyle\{[^}]*\}|bibliography\{[^}]*\}|usepackage(\[[^\]]*\])?\{[^}]*\}|author\{[^}]*\}|date\{[^}]*\})/g, "");
  const html = s.split(/\n\s*\n/).map((p) => {
    const t = p.trim(); if (!t) return "";
    if (/^(<h\d|<div|<ul|<ol|@@B)/.test(t)) return t.replace(/@@B(\d+)@@/g, (_, n) => blocks[+n]);
    return "<p>" + texInline(t).replace(/@@B(\d+)@@/g, (_, n) => blocks[+n]) + "</p>";
  }).join("\n");
  return html.replace(/@@B(\d+)@@/g, (_, n) => blocks[+n]);
}

// ---------------------------------------------------------------- BibTeX
function bibToHtml(src) {
  const ents = [...src.matchAll(/@(\w+)\s*\{\s*([^,]+),([\s\S]*?)\n\}/g)];
  if (!ents.length) return "<pre class='r-code'>" + esc(src) + "</pre>";
  const f = (body, k) => { const m = body.match(new RegExp(k + "\\s*=\\s*[{\"]([\\s\\S]*?)[}\"]\\s*,?\\s*\\n", "i")); return m ? texInline(m[1].replace(/[{}]/g, "")) : ""; };
  return "<ol class='r-bib'>" + ents.map(([, type, key, body]) =>
    `<li><b>${f(body, "title") || esc(key)}</b><br/><span>${f(body, "author")}</span> · <i>${f(body, "journal") || f(body, "booktitle") || f(body, "publisher") || esc(type)}</i> ${f(body, "year")}<div class='r-note'>${esc(key)}</div></li>`).join("") + "</ol>";
}

// ---------------------------------------------------------------- components
function Html({ html, cls }) { return <div className={"r-doc " + (cls || "")} dangerouslySetInnerHTML={{ __html: html }} />; }

function JsonNode({ k, v, depth }) {
  const [open, setOpen] = useState(depth < 2);
  const isObj = v && typeof v === "object";
  if (!isObj) return (
    <div className="r-json-row"><span className="r-json-k">{k}</span>
      <span className={"r-json-v " + typeof v}>{v === null ? "null" : typeof v === "string" ? v : String(v)}</span></div>
  );
  const entries = Array.isArray(v) ? v.map((x, i) => [i, x]) : Object.entries(v);
  return (
    <div className="r-json-node">
      <div className="r-json-row clickable" onClick={() => setOpen(!open)}>
        <span className="r-json-k">{open ? "▾" : "▸"} {k}</span>
        <span className="faint">{Array.isArray(v) ? `[${v.length}]` : `{${entries.length}}`}</span>
      </div>
      {open && <div className="r-json-children">{entries.map(([ck, cv]) => <JsonNode key={ck} k={String(ck)} v={cv} depth={depth + 1} />)}</div>}
    </div>
  );
}
function RowsTable({ rows }) {
  const cols = [...rows.slice(0, 400).reduce((s, r) => { Object.keys(r).forEach((k) => s.add(k)); return s; }, new Set())];
  const show = (x) => (x && typeof x === "object" ? JSON.stringify(x) : x === undefined ? "" : String(x));
  return (
    <div className="r-doc">
      <div className="faint" style={{ fontSize: 12, marginBottom: 8 }}>{rows.length} rows{rows.length > 400 ? " (first 400 shown)" : ""}</div>
      <table className="r-table"><thead><tr>{cols.map((c) => <th key={c}>{c}</th>)}</tr></thead>
        <tbody>{rows.slice(0, 400).map((r, i) => <tr key={i}>{cols.map((c) => <td key={c}>{show(r[c])}</td>)}</tr>)}</tbody></table>
    </div>
  );
}
function CodeView({ text }) {
  const lines = text.replace(/\n$/, "").split("\n");
  return <pre className="r-codeview">{lines.map((l, i) => <div key={i}><span className="r-ln">{i + 1}</span>{l || " "}</div>)}</pre>;
}

export function RenderedFile({ ext, text }) {
  const e = (ext || "").toLowerCase();
  try {
    if (e === ".md") return <Html html={mdToHtml(text)} />;
    if (e === ".tex") return <Html html={texToHtml(text)} cls="r-tex" />;
    if (e === ".bib") return <Html html={bibToHtml(text)} />;
    if (e === ".json") { const v = JSON.parse(text); return <div className="r-doc"><JsonNode k="(root)" v={v} depth={0} /></div>; }
    if (e === ".jsonl") return <RowsTable rows={text.split("\n").filter((l) => l.trim()).map((l) => { try { return JSON.parse(l); } catch { return { line: l }; } })} />;
    if (e === ".csv") {
      const L = text.trim().split("\n"); const h = L[0].split(",");
      return <RowsTable rows={L.slice(1).map((l) => { const c = l.split(","); const o = {}; h.forEach((k, i) => (o[k] = c[i])); return o; })} />;
    }
  } catch (err) { /* fall through to the code view if a file is malformed */ }
  return <CodeView text={text} />;
}
