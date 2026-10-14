"""Phase 4 — Jev mode: a LOCAL decider for Odin's CLOSED fixed-option decisions (P4a-3), trained on the M4.

Design (owner's spec P4b/P4c):
  * base: Qwen (free, full precision BF16 weights from Hugging Face), ALL layers intact and FROZEN (P4c-1);
  * one forward pass -> the hidden state of the last token -> a small DECISION HEAD per decision type that outputs
    one choice from the allowed list + a confidence (P4c-2); confidence calibrated by temperature scaling (P4c-3);
  * the STANDING context (Odin's agents, projects, decision definitions, standards) is PREPARED once as a cached
    prefix (KV cache); each decision only adds its new part as an offset (P4c-4);
  * confidence below the calibrated threshold -> automatic fallback to the LLM (P4c-5).
Mode setting (P4e): data/decider_mode.json {"mode": "normal"|"jev"}; default NORMAL. In normal mode nothing here
runs and Odin behaves exactly as before. Every Jev decision is logged (mode, confidence, timing, fallback)."""
from __future__ import annotations
import json, os, pathlib, threading, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODE_FILE = ROOT / "data" / "decider_mode.json"
ART = pathlib.Path(os.environ.get("ODIN_JEV_DIR") or (ROOT / "data" / "jev"))
LOG = ROOT / "workspace" / "history" / "decisions.jsonl"
MODES = ("normal", "jev")

DECISIONS = {
    "D1_mode": {"options": ["direct", "orchestrate"],
                "ask": "Decide the MINIMAL handling of this owner message: direct (a single scoped task, a question, a confirmation, an approval or a read-only diagnosis) or orchestrate (genuinely needs several specialists building/deploying)."},
    "D2_agent": {"options": ["Frontend", "Backend", "DevOps & Cloud", "Security & Compliance", "QA & Testing", "Database", "CTO Brain"],
                 "ask": "Which specialist OWNS this request? Route by the ACTION, not by names inside file or folder names."},
    "D2_action": {"options": ["read", "change"],
                  "ask": "Does this request only READ/inspect state, or would it CHANGE state (deploy, restart, write, edit, install, migrate, delete, rotate, approve)? If unsure: change."},
    "D4_qa": {"options": ["no", "yes"],
              "ask": "Is adding a QA gate to this project genuinely important (real code changes, production, data integrity) and not ruled out by the owner?"},
    "D9_nature": {"options": ["technical", "operational"],
                  "ask": "Is this team member technical (writes or edits code, builds software components) or operational (operates platforms, reports, no code)?"},
}

STANDARDS = (
    "Odin is an agentic AI software company. The owner talks to it in chat (English, sometimes Arabic, often short and informal).\n"
    "Specialists: Frontend (UI, screens, web pages); Backend (APIs, services, business logic, integrations: orders, CRM contacts, email platform data, jobs, billing); "
    "DevOps & Cloud (servers/VMs on Azure, deploys, deploy lists, SSH with the dynamic-IP firewall protocol, nginx, systemd, networking); "
    "Security & Compliance (secrets, keys, auth, encryption, PII, audits, exposure, fake users and abuse); QA & Testing (tests, regressions, verification); "
    "Database (schema, migrations, queries, backups); CTO Brain (strategy, planning, greetings, questions about the assistant, status, anything else).\n"
    "Rules: route by the ACTION; reading = compare, list, show, status, check, count, questions; changing = deploy, restart, write, edit, install, migrate, delete, "
    "rotate firewall IPs, approve, redo a change. Direct = one scoped task or question; orchestrate = several specialists building/deploying.\n")


def standing_context() -> str:
    """The prepared, slowly-changing context (P4c-4): standards + real agents + real projects."""
    agents, projs = [], []
    try:
        for d in sorted((ROOT / "workspace" / "agents").iterdir()):
            f = d / "capability.md"
            if f.is_file():
                ls = [x for x in f.read_text(errors="replace").splitlines() if x.strip()]
                agents.append((ls[0].lstrip("# ").strip() if ls else d.name)[:90])
    except Exception:
        pass
    try:
        for d in sorted((ROOT / "workspace" / "projects").iterdir()):
            if d.is_dir() and not d.name.startswith("_"):
                projs.append(d.name)
    except Exception:
        pass
    return (STANDARDS + "Agents: " + "; ".join(agents) + "\nProjects: " + ", ".join(projs[:80]) + "\n")


def suffix(decision: str, text: str) -> str:
    d = DECISIONS[decision]
    return (f"\n### Decision {decision}\nOptions: {', '.join(d['options'])}\n{d['ask']}\nInput:\n{(text or '').strip()[:2500]}\nAnswer:")


# ── mode setting (P4e) ──
def get_mode() -> str:
    try:
        m = json.loads(MODE_FILE.read_text()).get("mode", "normal")
        return m if m in MODES else "normal"
    except Exception:
        return "normal"


def set_mode(m: str) -> str:
    if m not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    MODE_FILE.parent.mkdir(parents=True, exist_ok=True)
    MODE_FILE.write_text(json.dumps({"mode": m}))
    if m == "jev":
        prewarm()
    return m


def log_decision(rec: dict) -> None:
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG, "a") as f:
            f.write(json.dumps({"ts": time.time(), **rec}, ensure_ascii=False) + "\n")
    except Exception:
        pass


RARE = "_rare"   # a grouped class of options with too few training examples (< MIN_PER_CLASS); always falls back to the LLM
MIN_PER_CLASS = 20

# ── the model (lazy; only Jev mode or training loads it) ──
_LOCK = threading.Lock()
_M = {}


class Encoder:
    """Frozen Qwen + prepared-prefix KV cache. features(decision, text) -> last-token hidden state."""

    def __init__(self, model_dir: str, context: str | None = None, layer: str = "final"):
        import mlx.core as mx
        from mlx_lm import load
        from mlx_lm.models.cache import make_prompt_cache
        self.mx = mx
        self.model, self.tok = load(model_dir)
        self.model.freeze()                                    # P4c-1: base layers intact and frozen
        self.context = context if context is not None else standing_context()
        self.layer = layer                                     # which hidden state feeds the heads (P4 layer comparison)
        self.n_layers = len(self.model.model.layers)
        self._mk = make_prompt_cache
        t0 = time.time()
        ids = mx.array(self.tok.encode(self.context))[None]
        self.prefix = make_prompt_cache(self.model)
        self.model.model(ids, cache=self.prefix)               # prepare the standing context ONCE (P4c-4)
        mx.eval([c.state for c in self.prefix])
        self.prefix_tokens = int(ids.shape[1]); self.prefix_ms = (time.time() - t0) * 1000

    def _hidden(self, decision: str, text: str):
        """One forward pass over the new part only (prepared prefix reused). Returns the last token's state after EVERY
        block (index k-1 = 'layer k') and the final normed state — identical maths to the model's own forward."""
        mx = self.mx
        from mlx_lm.models.base import create_attention_mask
        cache = self._mk(self.model)
        for c, p in zip(cache, self.prefix):                   # reuse the prepared prefix; only the offset is new
            c.state = p.state
        ids = mx.array(self.tok.encode(suffix(decision, text), add_special_tokens=False))[None]
        m = self.model.model
        h = m.embed_tokens(ids)
        mask = create_attention_mask(h, cache[0])
        outs = []
        for layer, c in zip(m.layers, cache):
            h = layer(h, mask, c)
            outs.append(h[0, -1, :])
        return outs, m.norm(h)[0, -1, :]

    def pick(self, outs, final, spec: str):
        mx = self.mx
        if spec == "final":
            v = final
        elif spec.startswith("mean"):                          # e.g. "mean16-24" = mean of layers 16..24
            a, b = (int(x) for x in spec[4:].split("-"))
            v = mx.mean(mx.stack(outs[a - 1:b]), axis=0)
        elif spec.startswith("L"):
            v = outs[int(spec[1:]) - 1]
        else:
            raise ValueError(spec)
        return v.astype(mx.float32)

    def available(self, spec: str) -> bool:
        if spec == "final": return True
        if spec.startswith("mean"): return int(spec[4:].split("-")[1]) <= self.n_layers
        return int(spec[1:]) <= self.n_layers

    def features_specs(self, decision: str, text: str, specs):
        outs, final = self._hidden(decision, text)
        r = {sp: self.pick(outs, final, sp) for sp in specs if self.available(sp)}
        self.mx.eval(list(r.values()))
        return r

    def features(self, decision: str, text: str):
        return self.features_specs(decision, text, [self.layer])[self.layer]


def _load():
    with _LOCK:
        if "enc" in _M:
            return _M
        import mlx.core as mx
        meta = json.loads((ART / "meta.json").read_text())
        enc = Encoder(meta["model_dir"], context=(ART / "context.txt").read_text(), layer=meta.get("layer", "final"))
        heads = {}
        for k, h in meta["heads"].items():
            w = mx.load(str(ART / f"{k}.npz"))
            heads[k] = {"W1": w["W1"], "b1": w["b1"], "W2": w["W2"], "b2": w["b2"], "T": h["T"], "tau": h["tau"], "options": h["options"],
                        "off": h.get("off_classes", [])}
        _M.update(enc=enc, heads=heads, meta=meta)
        return _M


def head_probs(h: dict, v):
    import mlx.core as mx
    z = mx.maximum(v @ h["W1"] + h["b1"], 0) @ h["W2"] + h["b2"]
    return mx.softmax(z / h["T"], axis=-1)


def decide(decision: str, text: str) -> dict:
    """One local decision: {choice, confidence, ms, fallback}. fallback=True -> the caller must use the LLM."""
    t0 = time.time()
    try:
        m = _load()
        h = m["heads"].get(decision)
        if h is None:
            return {"choice": None, "confidence": 0.0, "ms": 0.0, "fallback": True, "why": "no head for this decision"}
        p = head_probs(h, m["enc"].features(decision, text))
        import mlx.core as mx
        i = int(mx.argmax(p).item()); conf = float(p[i].item())
        ch = h["options"][i]
        r = {"choice": ch, "confidence": round(conf, 4), "ms": round((time.time() - t0) * 1000, 1),
             "fallback": conf < h["tau"] or ch == RARE or ch in h.get("off", [])}
        if ch in h.get("off", []):                            # owner 2026-10-13: a class with < 5 independent test cases stays off
            r["why"] = "class off (too few independent cases) -> LLM"
        if ch == RARE:                                         # owner 2026-10-12: rarely seen classes are grouped; the LLM decides them
            r["why"] = "rare class group -> LLM"
    except Exception as e:
        r = {"choice": None, "confidence": 0.0, "ms": round((time.time() - t0) * 1000, 1), "fallback": True, "why": f"decider unavailable: {type(e).__name__}"}
    return r


def authority() -> str:
    """Owner 2026-10-13: Jev has NO live authority until the owner's labels arrive and the post-label re-run is done.
    'shadow' (default): in Jev mode the decider runs and is LOGGED, but the LLM path decides every case.
    'live': written into meta.json ONLY by the post-label re-run (after_labels.sh). Thresholds/calibration fitted
    on generated data are therefore never used for a live decision.
    'experiment': the isolated copy's measurement harness only (env ODIN_JEV_EXPERIMENT=1, never in production)."""
    if os.environ.get("ODIN_JEV_EXPERIMENT") == "1":
        return "experiment"
    try:
        a = json.loads((ART / "meta.json").read_text()).get("authority", "shadow")
        return a if a in ("shadow", "live") else "shadow"
    except Exception:
        return "shadow"


def jev_choice(decision: str, text: str):
    """Call sites use this: None in Normal mode, on fallback, or in SHADOW (the caller then runs its LLM path
    unchanged); otherwise the local decision. Every Jev decision is logged (P4e-3), shadow ones included."""
    if get_mode() != "jev":
        return None
    a = authority()
    if a == "shadow":
        # v2 (cutover check A): in SHADOW the answer is never used, so the decider must not sit on the request path.
        # It runs on a background worker (serialised, same log record) and the caller continues at once.
        _shadow_submit(decision, text)
        return None
    r = _decide_and_log(decision, text, a)
    return None if r.get("fallback") else r.get("choice")


_WORK = threading.Lock()
_PENDING: list = []


def _decide_and_log(decision: str, text: str, a: str) -> dict:
    with _WORK:                                    # one decision at a time on the GPU
        r = decide(decision, text)
    log_decision({"mode": "jev", "authority": a, "decision": decision, "choice": r.get("choice"), "confidence": r.get("confidence"),
                  "ms": r.get("ms"), "fallback": r.get("fallback"), "why": r.get("why", ""), "used": a != "shadow" and not r.get("fallback")})
    return r


def _shadow_submit(decision: str, text: str) -> None:
    t = threading.Thread(target=_decide_and_log, args=(decision, text, "shadow"), daemon=True)
    _PENDING.append(t); t.start()
    _PENDING[:] = [x for x in _PENDING if x.is_alive()]


def flush(timeout: float = 30.0) -> None:
    """Wait for background shadow decisions (tests, shutdown)."""
    for t in list(_PENDING):
        t.join(timeout)


def prewarm() -> None:
    """v2 (cutover check A): load the model + standing-context cache in the background as soon as Jev mode is on,
    so the first real decision does not pay the ~1.5 s cold start."""
    def _w():
        try:
            if (ART / "meta.json").is_file():
                with _WORK:
                    _load()
                    decide("D1_mode", "warm-up")
        except Exception:
            pass
    threading.Thread(target=_w, daemon=True).start()


def log_llm(decision: str, choice, ms: float) -> None:
    """The LLM path's decision (Normal mode, or a Jev fallback) — same log, mode recorded."""
    log_decision({"mode": get_mode(), "decision": decision, "choice": choice, "confidence": None, "ms": round(ms, 1),
                  "fallback": get_mode() == "jev", "by": "llm"})
