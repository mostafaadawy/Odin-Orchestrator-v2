"""
Meeting monitor backend — the reusable "live meeting" ASSET (web/desktop/mobile share ONE UI).

This capability is owned by the **Live Meeting & Voice Streaming Agent** role (see agents_registry /
projects role catalog). Any project that has that agent gets the 🎙 listener beside the ▶ button and
uses THIS asset: capture voice in serial chunks → transcribe live → detect each chunk's language →
build a smart report → export it as Markdown or Word, in Arabic OR English.

Flow the UI drives:
  • GET  /meeting/state?pid=      -> how many saved chunks exist (offer "clean & start fresh")
  • POST /meeting/clear?pid=      -> DELETE the saved chunk files from disk (only the chunks)
  • POST /meeting/chunk?pid=      -> upload ONE audio chunk (multipart 'file'); saved + transcribed +
                                     per-chunk language detected
  • POST /meeting/finish?pid=     -> merge transcripts, pick majority language, build the report in it
  • GET  /meeting/view?pid=&lang= -> {markdown, lang}  (build/cache the report in that language, for display)
  • GET  /meeting/report?pid=&fmt=md|docx&lang=ar|en  -> download the report (4 combinations)

Nothing is invented: missing owner/deadline/etc. are marked 'not mentioned' (same rules as the spec).
"""
from __future__ import annotations
import os, re, io, json, time, pathlib
from collections import Counter
from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse

import store        # type: ignore
import scopes        # type: ignore

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _dir(pid: str) -> pathlib.Path:
    d = store.WS / "projects" / pid / "data" / "meeting_chunks"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _manifest_path(pid: str) -> pathlib.Path:
    return _dir(pid) / "manifest.json"


def _load_manifest(pid: str) -> list:
    p = _manifest_path(pid)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return []
    return []


def _save_manifest(pid: str, rows: list) -> None:
    _manifest_path(pid).write_text(json.dumps(rows, ensure_ascii=False, indent=2))


def _detect_lang(text: str) -> str:
    """Majority language of a piece of text: 'ar' if Arabic script dominates, else 'en'."""
    ar = sum(1 for c in text if "؀" <= c <= "ۿ")
    en = sum(1 for c in text if c.isascii() and c.isalpha())
    if ar == 0 and en == 0:
        return "en"
    return "ar" if ar >= en else "en"


# ---- speech refinement (bilingual, confidence, noise) — same spirit as the desktop refinement -------
# Protected tokens we NEVER drop even if they look like foreign "noise": names, products, commands,
# APIs, file/service/project names. Heuristic: CamelCase, dotted.names, ALLCAPS, code-ish tokens.
# single- and multi-word fillers (EN + Egyptian/MSA Arabic)
_FILLER = {"um", "uh", "erm", "hmm", "uhh", "umm", "ah", "eh", "mm", "like", "so", "basically",
           "actually", "literally", "kind of", "sort of", "you know", "i mean",
           "يعني", "امم", "اممم", "ايه", "اه", "اها", "طب", "يعنى", "زي", "كده", "بقى", "خلاص"}
_FILLER_PHRASES = ("you know", "i mean", "kind of", "sort of")
# Protected tokens we NEVER drop even if they look like foreign "noise": names, products, commands,
# APIs, file/service/project names. CamelCase, dotted.names, ALLCAPS, paths, code-ish, file extensions.
# CASE-SENSITIVE on purpose: CamelCase, dotted.names, ALLCAPS, paths, file extensions.
_PROTECT_RE = re.compile(r"([A-Z][a-zA-Z0-9]+[A-Z][a-zA-Z0-9]*|[a-zA-Z0-9_]+\.[a-zA-Z0-9_.]+|"
                         r"\b[A-Z]{2,}\b|/[\w./-]+|\b\w+\.(?:ts|js|py|json|env|sh|md|yml|yaml)\b)")
_ARABIC_RE = re.compile(r"[؀-ۿ]")
# case-insensitive technical vocabulary (kept even as lone tokens inside the other language)
_TECH_EN = {"api", "app", "build", "deploy", "server", "backend", "frontend", "database", "db",
            "prisma", "nginx", "vm", "git", "npm", "npx", "node", "stripe", "webhook", "token", "login",
            "release", "commit", "branch", "port", "cache", "queue", "cron", "log", "docker",
            "ssh", "sql", "http", "https", "url", "next", "nest", "redis", "kafka"}


def _protected_terms(text: str) -> list:
    return list({m.group(0) for m in _PROTECT_RE.finditer(text or "")})


def _is_protected(word: str) -> bool:
    w = word.strip(".,!?؛،:()[]\"'").strip()
    if not w:
        return False
    if _PROTECT_RE.search(w):
        return True
    if w.lower() in _TECH_EN:
        return True
    if w[:1].isupper() and w[1:].islower() and len(w) > 2:  # a Name (proper noun)
        return True
    if any(ch.isdigit() for ch in w):                       # dates/versions/numbers
        return True
    return False


def _refine(text: str, target_lang: str) -> str:
    """STRONG bilingual refinement (full-conversation scale). Removes fillers, repeated phrases, broken
    fragments, and stray minority-language noise — while PRESERVING protected terms (names, commands,
    APIs, files, dates, numbers). If the session is mainly Arabic, isolated English fragments that are
    NOT protected/technical are dropped; if mainly English, isolated Arabic non-name noise is dropped."""
    if not text or not text.strip():
        return ""
    protect_all = set(_protected_terms(text))
    # 1) strip multi-word filler phrases first
    low = text
    for ph in _FILLER_PHRASES:
        low = re.sub(rf"\b{re.escape(ph)}\b", " ", low, flags=re.I)
    words = low.split()
    maj = target_lang if target_lang in ("ar", "en") else _detect_lang(text)
    kept = []
    for w in words:
        core = w.strip(".,!?؛،:()[]\"'").lower()
        if not core:
            continue
        if core in _FILLER:                       # 2) drop fillers
            continue
        is_ar = bool(_ARABIC_RE.search(w))
        # 3) minority-language stray noise: single short opposite-script token that isn't protected
        if maj == "ar" and not is_ar and not _is_protected(w) and len(core) <= 3:
            continue
        if maj == "en" and is_ar and not _is_protected(w) and len(core) <= 2:
            continue
        # 4) broken 1-char fragments (non-protected, non-alnum-meaning)
        if len(core) == 1 and not _is_protected(w) and not core.isdigit():
            continue
        kept.append(w)
    # 5) collapse consecutive duplicate words AND 2-3 word repeated phrases
    dedup = []
    for w in kept:
        if dedup and dedup[-1].lower() == w.lower():
            continue
        dedup.append(w)
    for n in (3, 2):
        i = 0; res = []
        while i < len(dedup):
            if i + 2 * n <= len(dedup) and [x.lower() for x in dedup[i:i+n]] == [x.lower() for x in dedup[i+n:i+2*n]]:
                res.extend(dedup[i:i+n]); i += 2 * n
            else:
                res.append(dedup[i]); i += 1
        dedup = res
    cleaned = re.sub(r"\s+", " ", " ".join(dedup)).strip(" ,.")
    # 6) guarantee protected terms survived
    for p in protect_all:
        if p and p not in cleaned and p in text:
            cleaned = (cleaned + " " + p).strip()
    return cleaned   # empty when the segment was all noise/filler -> marked low-confidence downstream


def _noise_score(raw: str, cleaned: str) -> float:
    """0..1 — fraction removed as noise. Higher = noisier."""
    r = len((raw or "").split()); c = len((cleaned or "").split())
    if r == 0:
        return 1.0
    return round(max(0.0, min(1.0, 1 - (c / r))), 2)


def _confidence(cleaned: str, noise: float, raw: str = "") -> float:
    """0..1 confidence from multiple signals: content length, how much was noise, and the share of
    real/meaningful words. Very short, very noisy, or all-filler segments score low (get marked)."""
    words = (cleaned or "").split()
    if not words:
        return 0.0
    length_sig = min(1.0, len(words) / 8.0)                 # ~8+ words reads as a full thought
    real = sum(1 for w in words if len(w.strip(".,!?؛،")) > 2 or _is_protected(w))
    real_ratio = real / max(1, len(words))
    conf = (0.5 * length_sig + 0.5 * real_ratio) * (1 - 0.6 * noise)
    return round(max(0.0, min(1.0, conf)), 2)


def _chunk_meta(idx: int, raw: str, start_s: float = 0.0, end_s: float = 0.0,
                speaker: str = "") -> dict:
    """Build the full spec chunk record: id, timestamps, language, speaker, raw + cleaned, noise,
    confidence, topic, operational points, status."""
    lang = _detect_lang(raw)
    cleaned = _refine(raw, lang)
    noise = _noise_score(raw, cleaned)
    conf = _confidence(cleaned, noise, raw)
    low = raw.lower()
    ops = []
    for kw, label in (("decision", "decision"), ("agreed", "decision"), ("action", "action item"),
                      ("deadline", "deadline"), ("risk", "risk"), ("blocker", "blocker"),
                      ("قرار", "decision"), ("مهمة", "action item"), ("خطر", "risk")):
        if kw in low:
            ops.append(label)
    return {
        "id": f"{idx:03d}",
        "start": round(start_s, 1), "end": round(end_s, 1),
        "lang": lang, "speaker": speaker or "",
        "raw": raw, "text": cleaned,
        "noise_score": noise, "confidence": conf,
        "topic": (cleaned.split(".")[0][:60] if cleaned else ""),
        "operational_points": sorted(set(ops)),
        "status": ("low_confidence" if conf < 0.35 else "processed"),
        "note": ("Chunk confidence low. Content may require user review." if conf < 0.35 else ""),
        "ts": time.time(),
    }


def _majority_lang(rows: list) -> str:
    """Majority language ACROSS chunks, weighted by transcript length (per-chunk detection)."""
    weight = Counter()
    for x in rows:
        t = x.get("text") or ""
        if not t.strip():
            continue
        weight[x.get("lang") or _detect_lang(t)] += len(t)
    if not weight:
        return "en"
    return weight.most_common(1)[0][0]


def _engine(prompt: str) -> str:
    """Raw model call — NOT /chat (which is propose-first and would refuse 'sensitive' content)."""
    os.environ.setdefault("ODIN_CLAUDE_TOOLS", "Read,Glob,Grep")
    try:
        import projects  # type: ignore
        out = (projects._engine(prompt) or "").strip()
    except Exception:
        return ""
    low = out.lower()
    if not out or "engine offline" in low or "needs your approval" in low or "cannot compute" in low:
        return ""
    return out


REPORT_EN = ("You are a meeting-intelligence agent. From the meeting transcript below (which may be in any "
    "language), produce ONE smart report **written entirely in English** using EXACTLY these 13 sections and "
    "nothing else: 1 Meeting Overview, 2 Executive Summary, 3 Important Notifications, 4 Decisions Made, "
    "5 Proposed Decisions, 6 Completed Items, 7 Pending Items, 8 Action Items (Task/Owner/Deadline/Priority/"
    "Status), 9 Risks and Blockers, 10 Recommendations, 11 Follow-Up Messages, 12 Suggested Next Meeting "
    "Agenda, 13 Open Questions. Merge duplicates; separate confirmed vs proposed and completed vs pending. "
    "Mark any missing owner/deadline/info as 'not mentioned'. Invent nothing. Output Markdown.\n\nTRANSCRIPT:\n{t}")

REPORT_AR = ("أنت وكيل ذكاء اجتماعات. من نص الاجتماع بالأسفل (قد يكون بأي لغة)، أنشئ تقريرًا ذكيًا واحدًا "
    "**مكتوبًا بالكامل باللغة العربية** باستخدام هذه الأقسام الـ13 حصرًا ولا شيء غيرها: 1 نظرة عامة على الاجتماع، "
    "2 ملخص تنفيذي، 3 تنبيهات مهمة، 4 القرارات المتخذة، 5 القرارات المقترحة، 6 العناصر المكتملة، 7 العناصر المعلّقة، "
    "8 عناصر العمل (المهمة/المسؤول/الموعد النهائي/الأولوية/الحالة)، 9 المخاطر والعوائق، 10 التوصيات، 11 رسائل المتابعة، "
    "12 جدول أعمال الاجتماع القادم المقترح، 13 أسئلة مفتوحة. ادمج التكرارات، وافصل القرارات المؤكدة عن المقترحة "
    "والمكتمل عن المعلّق. اكتب 'غير مذكور' لأي مسؤول/موعد/معلومة ناقصة. لا تختلق شيئًا. أخرج بصيغة ماركداون.\n\n"
    "النص:\n{t}")


def _fallback_report(transcript: str, lang: str) -> str:
    n = len([l for l in transcript.splitlines() if l.strip()])
    if lang == "ar":
        return (f"# تقرير الاجتماع الذكي\n\n## 1. نظرة عامة على الاجتماع\nعدد الأسطر: {n}\n\n"
                "## 2. ملخص تنفيذي\n(المحرّك غير متصل — دُمجت المقاطع نصيًا.)\n\n"
                "## 8. عناصر العمل\n(المسؤول/الموعد: غير مذكور حيثما غاب)\n\n## 13. أسئلة مفتوحة\n(من النص)\n")
    return (f"# Meeting Smart Report\n\n## 1. Meeting Overview\nLines: {n}\n\n"
            "## 2. Executive Summary\n(Engine offline — transcripts merged structurally.)\n\n"
            "## 8. Action Items\n(Owner/Deadline marked 'not mentioned' where absent)\n\n"
            "## 13. Open Questions\n(collected from transcript)\n")


def _transcript(pid: str) -> str:
    rows = _load_manifest(pid)
    parts = []
    for x in rows:
        t = (x.get("text") or "").strip()
        if not t:
            continue
        conf = x.get("confidence")
        flag = "  ⚠️(low confidence — may need review)" if (isinstance(conf, (int, float)) and conf < 0.35) else ""
        parts.append(f"[chunk {x['id']} · {x.get('lang','?')}] {t}{flag}")
    return "\n".join(parts)


def _build_report(pid: str, lang: str) -> str:
    """Build (and cache) the report in the requested language from the merged transcript."""
    lang = "ar" if lang == "ar" else "en"
    cache = _dir(pid) / f"report_{lang}.md"
    if cache.exists():
        return cache.read_text(encoding="utf-8")
    transcript = _transcript(pid)
    if not transcript.strip():
        md = _fallback_report("", lang)
    else:
        tmpl = REPORT_AR if lang == "ar" else REPORT_EN
        md = _engine(tmpl.format(t=transcript[:12000])) or _fallback_report(transcript, lang)
    cache.write_text(md, encoding="utf-8")
    return md


def _shade(paragraph, hex_fill: str):
    """Apply a background shade to a paragraph (colorful section bands)."""
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    pPr = paragraph._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hex_fill)
    pPr.append(shd)


def _md_to_pdf_bytes(md: str, title: str, lang: str = "en") -> bytes:
    """Styled PDF export of the meeting report (headings in brand color; simple, clean layout)."""
    import io as _io
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    buf = _io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm, bottomMargin=16 * mm,
                            leftMargin=18 * mm, rightMargin=18 * mm, title=title)
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("H1", parent=ss["Title"], textColor=colors.HexColor("#2B5CE0"), fontSize=18, spaceAfter=10)
    h2 = ParagraphStyle("H2", parent=ss["Heading2"], textColor=colors.HexColor("#1F9A61"), fontSize=13, spaceBefore=8)
    body = ParagraphStyle("Body", parent=ss["BodyText"], fontSize=10.5, leading=15,
                          alignment=(2 if lang == "ar" else 0))
    flow = [Paragraph(title, h1), Spacer(1, 6)]
    for raw in (md or "").splitlines():
        ln = raw.rstrip()
        if not ln:
            flow.append(Spacer(1, 4)); continue
        if ln.startswith("### "):
            flow.append(Paragraph(ln[4:], h2))
        elif ln.startswith("## "):
            flow.append(Paragraph(ln[3:], h2))
        elif ln.startswith("# "):
            flow.append(Paragraph(ln[2:], h1))
        else:
            safe = ln.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            flow.append(Paragraph(safe, body))
    doc.build(flow)
    return buf.getvalue()


def _md_to_docx_bytes(md: str, title: str, lang: str = "en") -> bytes:
    """Clean, professional, COLORFUL, structured Word export (headings in brand colors, shaded section
    bands, styled title, RTL for Arabic)."""
    from docx import Document
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    BRAND = RGBColor(0x2B, 0x5C, 0xE0)      # blue
    ACCENT = RGBColor(0x1F, 0x9A, 0x61)     # green
    DARK = RGBColor(0x22, 0x27, 0x38)
    rtl = (lang == "ar")

    doc = Document()
    normal = doc.styles["Normal"]; normal.font.name = "Calibri"; normal.font.size = Pt(11)

    # ---- styled title band ----
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = t.add_run(title); run.bold = True; run.font.size = Pt(22); run.font.color.rgb = BRAND
    _shade(t, "EAF0FF")
    sub = doc.add_paragraph(); sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sr = sub.add_run("Generated by the Live Meeting & Voice Streaming Agent")
    sr.italic = True; sr.font.size = Pt(9); sr.font.color.rgb = DARK
    doc.add_paragraph("")

    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip():
            doc.add_paragraph("")
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            lvl = len(m.group(1)); p = doc.add_paragraph()
            if rtl: p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            r = p.add_run(m.group(2)); r.bold = True
            r.font.size = Pt(16 if lvl <= 1 else 13 if lvl == 2 else 11.5)
            r.font.color.rgb = BRAND if lvl <= 2 else ACCENT
            if lvl <= 2: _shade(p, "F2F6FF")
            continue
        if re.match(r"^\s*[-*•]\s+", line):
            p = doc.add_paragraph(re.sub(r"^\s*[-*•]\s+", "", line), style="List Bullet")
            if rtl: p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            continue
        mnum = re.match(r"^\s*\d+[.)]\s+(.*)$", line)
        if mnum:
            p = doc.add_paragraph(mnum.group(1), style="List Number")
            if rtl: p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            continue
        p = doc.add_paragraph()
        if rtl: p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        # bold **spans**
        for i, seg in enumerate(re.split(r"\*\*(.+?)\*\*", line)):
            rr = p.add_run(seg); rr.bold = (i % 2 == 1); rr.font.size = Pt(11)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def build_router() -> APIRouter:
    r = APIRouter()

    @r.get("/meeting/capable")
    def capable(pid: str):
        """Does this project own the live-meeting asset (has the Live Meeting & Voice Streaming Agent,
        or an agent whose role matches the signature)? The app shows the 🎙 listener only when true —
        so the capability TRAVELS with the agent into any project it's added to."""
        try:
            import projects
            return {"pid": pid, "capable": bool(projects.project_has_meeting_asset(pid))}
        except Exception as e:
            return {"pid": pid, "capable": False, "error": str(e)}

    @r.get("/meeting/state")
    def state(pid: str):
        rows = _load_manifest(pid)
        return {"pid": pid, "count": len(rows),
                "chunks": [{"id": x.get("id"), "chars": len(x.get("text", "")), "lang": x.get("lang"),
                            "confidence": x.get("confidence"), "noise_score": x.get("noise_score"),
                            "status": x.get("status"), "topic": x.get("topic"),
                            "operational_points": x.get("operational_points")} for x in rows],
                "lowConfidence": sum(1 for x in rows if (x.get("confidence") or 1) < 0.35),
                "hasReport": (_dir(pid) / "report_en.md").exists() or (_dir(pid) / "report_ar.md").exists(),
                "majorityLang": _majority_lang(rows)}

    @r.post("/meeting/clear")
    def clear(pid: str):
        d = _dir(pid)
        removed = 0
        for f in d.glob("*"):
            try:
                f.unlink(); removed += 1
            except Exception:
                pass
        return {"cleared": removed}

    @r.post("/meeting/chunk")
    async def chunk(pid: str, file: UploadFile = File(...)):
        rows = _load_manifest(pid)
        idx = len(rows) + 1
        ext = (os.path.splitext(file.filename or "")[1] or ".webm")
        name = f"chunk_{idx:03d}{ext}"
        path = _dir(pid) / name
        data = await file.read()
        path.write_bytes(data)
        text = ""
        try:
            text = scopes.transcribe(str(path)) or ""
        except Exception:
            text = ""
        row = _chunk_meta(idx, text)          # full spec metadata: lang, cleaned, noise, confidence, topic, status…
        row["file"] = name; row["bytes"] = len(data)
        rows.append(row)
        _save_manifest(pid, rows)
        # a new chunk invalidates cached reports
        for lc in ("report_en.md", "report_ar.md"):
            try: (_dir(pid) / lc).unlink()
            except Exception: pass
        return {"id": row["id"], "text": row["text"], "lang": row["lang"],
                "confidence": row["confidence"], "noise_score": row["noise_score"],
                "status": row["status"], "note": row["note"], "count": len(rows)}

    @r.post("/meeting/finish")
    def finish(pid: str, body: dict | None = None):
        rows = _load_manifest(pid)
        forced = (body or {}).get("lang") if isinstance(body, dict) else None
        lang = forced or _majority_lang(rows) or "en"
        md = _build_report(pid, lang)
        # post the report into the project chat (attributed) so it's also visible in the conversation
        try:
            cid = scopes.create_chat(f"project:{pid}", title="🎙️ Meeting report")["id"]
            scopes.add_message(f"project:{pid}", cid, "assistant",
                               ("تقرير الاجتماع:\n\n" if lang == "ar" else "Meeting report:\n\n") + md,
                               sender="Live Meeting & Voice Streaming Agent")
        except Exception:
            pass
        return {"markdown": md, "lang": lang, "chunks": len(rows),
                "langs": {"en": True, "ar": True}}  # both are exportable/translatable on demand

    @r.post("/meeting/finish_text")
    def finish_text(pid: str, body: dict | None = None):
        """MOBILE path: the phone transcribes on-device (speech_to_text) and posts the chunk TEXTS here
        (no audio upload). We store them as the manifest — so /meeting/view, /meeting/report and docx
        export all work identically — then build the report in the majority (or forced) language."""
        body = body or {}
        texts = body.get("texts")
        if not isinstance(texts, list):
            t = body.get("transcript") or ""
            texts = [s for s in re.split(r"\n{2,}", t) if s.strip()] or ([t] if t.strip() else [])
        rows = []
        for i, tx in enumerate(texts, 1):
            row = _chunk_meta(i, (tx or "").strip())   # full spec metadata for the mobile text path too
            row["file"] = ""; row["bytes"] = 0
            rows.append(row)
        _save_manifest(pid, rows)
        for lc in ("report_en.md", "report_ar.md"):
            try: (_dir(pid) / lc).unlink()
            except Exception: pass
        lang = body.get("lang") or _majority_lang(rows) or "en"
        md = _build_report(pid, lang)
        try:
            cid = scopes.create_chat(f"project:{pid}", title="🎙️ Meeting report")["id"]
            scopes.add_message(f"project:{pid}", cid, "assistant",
                               ("تقرير الاجتماع:\n\n" if lang == "ar" else "Meeting report:\n\n") + md,
                               sender="Live Meeting & Voice Streaming Agent")
        except Exception:
            pass
        return {"markdown": md, "lang": lang, "chunks": len(rows), "langs": {"en": True, "ar": True}}

    @r.get("/meeting/view")
    def view(pid: str, lang: str = "en"):
        return {"markdown": _build_report(pid, lang), "lang": ("ar" if lang == "ar" else "en")}

    @r.get("/meeting/report")
    def report(pid: str, fmt: str = "md", lang: str = "en"):
        rows = _load_manifest(pid)
        if not rows:
            return JSONResponse({"error": "no meeting captured yet"}, status_code=404)
        lang = "ar" if lang == "ar" else "en"
        md = _build_report(pid, lang)
        suffix = "ar" if lang == "ar" else "en"
        if fmt == "docx":
            data = _md_to_docx_bytes(md, "تقرير الاجتماع" if lang == "ar" else "Meeting Report", lang)
            return StreamingResponse(io.BytesIO(data),
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={"Content-Disposition": f'attachment; filename="meeting_report_{suffix}.docx"'})
        if fmt == "pdf":
            data = _md_to_pdf_bytes(md, "تقرير الاجتماع" if lang == "ar" else "Meeting Report", lang)
            return StreamingResponse(io.BytesIO(data), media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="meeting_report_{suffix}.pdf"'})
        return StreamingResponse(io.BytesIO(md.encode("utf-8")), media_type="text/markdown",
                headers={"Content-Disposition": f'attachment; filename="meeting_report_{suffix}.md"'})

    @r.get("/meeting/report_all")
    def report_all(pid: str):
        """Option 5 — GENERATE ALL FOUR: Arabic MD, English MD, Arabic DOCX, English DOCX, in one .zip."""
        rows = _load_manifest(pid)
        if not rows:
            return JSONResponse({"error": "no meeting captured yet"}, status_code=404)
        import zipfile
        md_en = _build_report(pid, "en"); md_ar = _build_report(pid, "ar")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("meeting_report_en.md", md_en)
            z.writestr("meeting_report_ar.md", md_ar)
            z.writestr("meeting_report_en.docx", _md_to_docx_bytes(md_en, "Meeting Report", "en"))
            z.writestr("meeting_report_ar.docx", _md_to_docx_bytes(md_ar, "تقرير الاجتماع", "ar"))
            z.writestr("meeting_report_en.pdf", _md_to_pdf_bytes(md_en, "Meeting Report", "en"))
            z.writestr("meeting_report_ar.pdf", _md_to_pdf_bytes(md_ar, "تقرير الاجتماع", "ar"))
        buf.seek(0)
        return StreamingResponse(buf, media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="meeting_report_all.zip"'})

    return r
