// v2 PAPER tab — every research file inside the v2 folder, scanned live from fixed research roots (so new or
// updated files appear automatically). The renderer can only ask for a path that is IN this list (relative,
// inside a root) — never an arbitrary path. Files are read from disk and handed over as base64.
const fs = require("fs");
const path = require("path");
const os = require("os");

const PROV = "provisional numbers — pending labels";
// Built-in catalog = fallback only. The LIVE catalog is <v2>/research/paper_catalog.json, read on every list()
// call, so new groups/labels/files appear without rebuilding the app.
const DEFAULT = {
  roots: [
    { dir: "research/paper-v1/paper-v1-submission", group: "Paper v1 — Odin-Orchestrator (frozen, submission copy, due 30 Oct)", status: "submission copy — frozen" },
    { dir: "research/paper-v2", group: "Paper v2 — Jev local decider (NEW, provisional until labels)", status: PROV },
    { dir: "research/resulted-papers-and-documents", group: "Other papers & documents", status: "document" },
  ],
  singles: [
    { file: "CHANGES.md", group: "Records", status: "current" },
    { file: "CHANGELOG.md", group: "Records", status: "current" },
  ],
};
function catalog(root) {
  try {
    const c = JSON.parse(fs.readFileSync(path.join(root, "research", "paper_catalog.json"), "utf8"));
    if (Array.isArray(c.roots)) return { roots: c.roots, singles: Array.isArray(c.singles) ? c.singles : [] };
  } catch {}
  return DEFAULT;
}
const MIME = { ".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".svg": "image/svg+xml" };
const TEXT = new Set([".md", ".tex", ".json", ".jsonl", ".csv", ".bib", ".bbl", ".py", ".txt", ".sty", ".cls", ".log"]);
const DOCX = /\.(docx|doc|rtf|odt)$/i;   // shown as plain text (macOS textutil); Download gives the original
const ARCH = /\.(zip|tgz|tar\.gz|tar)$/i;   // shown as a list of the files inside (download gives the archive)
const SKIP = new Set([".aux", ".out", ".fls", ".fdb_latexmk", ".synctex", ".DS_Store"]);

function walk(root, rel, out) {
  let ents = [];
  try { ents = fs.readdirSync(path.join(root, rel), { withFileTypes: true }); } catch { return; }
  for (const e of ents) {
    if (e.name.startsWith(".")) continue;
    const r = path.join(rel, e.name);
    if (e.isDirectory()) walk(root, r, out);
    else if (!SKIP.has(path.extname(e.name))) out.push(r);
  }
}
function list(root) {
  const items = []; const C = catalog(root);
  for (const R of C.roots) {
    let files = []; walk(root, R.dir, files);
    const relOf = (f) => path.relative(R.dir, f).split(path.sep).join("/");
    if (R.only) { const rx = new RegExp(R.only); files = files.filter((f) => rx.test(relOf(f))); }
    if (R.skip) { const rx = new RegExp(R.skip); files = files.filter((f) => !rx.test(relOf(f))); }
    // main papers first: PDFs directly in the root, then everything else by folder depth, then name
    const rank = (f) => { const rel = path.relative(R.dir, f); const d = rel.split(path.sep).length - 1;
      return [d === 0 && f.endsWith(".pdf") ? 0 : 1, d, rel]; };
    files.sort((a, b) => { const x = rank(a), y = rank(b); return x[0] - y[0] || x[1] - y[1] || x[2].localeCompare(y[2]); });
    for (const f of files) {
      const d = path.dirname(path.relative(R.dir, f)); const sub0 = d === "." ? "" : d;
      const sub = R.prefix ? (sub0 ? R.prefix + "/" + sub0 : R.prefix) : sub0;
      items.push({ id: f, file: f, group: R.group, root: R.dir, sub, title: path.basename(f), status: R.status });
    }
  }
  for (const S of C.singles) items.push({ id: S.file, file: S.file, group: S.group, root: "", sub: "", title: path.basename(S.file), status: S.status });
  return items.map((c) => {
    let st = null; try { st = fs.statSync(path.join(root, c.file)); } catch {}
    const ext = path.extname(c.file).toLowerCase();
    let pages = 0;
    if (st && ext === ".pdf" && st.size < 60e6) {
      try { const t = fs.readFileSync(path.join(root, c.file)).toString("latin1");
            const cs = [...t.matchAll(/\/Count\s+(\d+)/g)].map((m) => +m[1]);
            const ps = (t.match(/\/Type\s*\/Page[^s]/g) || []).length;
            pages = Math.max(ps, cs.length ? Math.max(...cs) : 0); } catch {}
    }
    return { ...c, exists: !!st, size: st ? st.size : 0, mtime: st ? st.mtimeMs : 0, kind: ext.slice(1) || "file", pages, viewable: ext === ".pdf" || TEXT.has(ext) || !!MIME[ext] || ARCH.test(c.file) || DOCX.test(c.file) };
  });
}
function allowed(root, id) { return list(root).find((x) => x.id === id) || null; }
function read(root, id) {
  const c = allowed(root, id);
  if (!c) return { ok: false, error: "not in the paper list" };
  const p = path.join(root, c.file); const ext = path.extname(p).toLowerCase();
  if (DOCX.test(p)) {
    try {
      const out = require("child_process").execFileSync("textutil", ["-convert", "txt", "-stdout", p], { maxBuffer: 32e6 }).toString();
      return { ok: true, name: path.basename(p) + ".txt", mime: "text/plain", text: true, base64: Buffer.from(out).toString("base64"), ext: ".txt" };
    } catch (e) { return { ok: false, error: "could not open document: " + e.message }; }
  }
  if (ARCH.test(p)) {
    try {
      const cp = require("child_process");
      const out = /\.zip$/i.test(p) ? cp.execFileSync("unzip", ["-l", p], { maxBuffer: 32e6 }).toString()
                                     : cp.execFileSync("tar", ["-tvf", p], { maxBuffer: 32e6 }).toString();
      const t = `Archive: ${path.basename(p)} — files inside (use Download to get the archive itself)\n\n` + out;
      return { ok: true, name: path.basename(p) + ".txt", mime: "text/plain", text: true, base64: Buffer.from(t).toString("base64"), ext: ".txt" };
    } catch (e) { return { ok: false, error: "could not list archive: " + e.message }; }
  }
  try {
    const b = fs.readFileSync(p);
    return { ok: true, name: path.basename(p), mime: MIME[ext] || (TEXT.has(ext) ? "text/plain" : "application/octet-stream"),
             text: TEXT.has(ext), base64: b.toString("base64"), ext };
  } catch (e) { return { ok: false, error: "not found: " + c.file }; }
}
async function save(root, id, dialog) {
  const c = allowed(root, id);
  if (!c) return { ok: false, error: "not in the paper list" };
  const src = path.join(root, c.file);
  const res = await dialog.showSaveDialog({ title: "Save " + c.title, defaultPath: path.join(os.homedir(), "Downloads", path.basename(src)) });
  if (res.canceled || !res.filePath) return { ok: false, canceled: true };
  fs.copyFileSync(src, res.filePath);
  return { ok: true, path: res.filePath };
}
async function saveGroup(root, group, dialog) {
  const items = list(root).filter((x) => x.group === group && x.exists);
  if (!items.length) return { ok: false, error: "unknown group" };
  const res = await dialog.showOpenDialog({ title: "Choose where to save “" + group + "” (all files)", properties: ["openDirectory", "createDirectory"] });
  if (res.canceled || !res.filePaths[0]) return { ok: false, canceled: true };
  const safe = (t) => t.replace(/[\\/:*?"<>|]/g, "-").slice(0, 90).trim();
  const dest = path.join(res.filePaths[0], safe(group));
  for (const x of items) {
    const d = path.join(dest, ...x.sub.split("/").filter(Boolean).map(safe));
    fs.mkdirSync(d, { recursive: true });
    fs.copyFileSync(path.join(root, x.file), path.join(d, x.title));
  }
  return { ok: true, path: dest, count: items.length };
}
module.exports = { list, read, save, saveGroup, catalog };
