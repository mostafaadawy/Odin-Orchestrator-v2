"""P4e: wire Jev mode into the decision points (idempotent). Normal mode = unchanged code path."""
import pathlib
def edit(p, old, new, marker):
    s = pathlib.Path(p).read_text()
    if marker in s: print("skip", p, marker); return
    assert s.count(old) == 1, (p, old[:70], s.count(old))
    pathlib.Path(p).write_text(s.replace(old, new)); print("ok", p, marker)
# D1 — intent.classify_request
edit("server/intent.py", '''    # Engine-first (smart) — but ALWAYS fall back to the deterministic net if it fails.
    if engine is not None:''', '''    # P4e: Jev mode — the local decider answers the CLOSED choice; low confidence falls back to the engine below.
    if engine is not None:
        try:   # a message that rules anything out ("do not deploy", "no db rebase", "without", "stop") always goes
            import jev_decider as _jd   # to the engine, so owner exclusions are never handled with less care
            _jm = None if re.search(r"\\b(do not|don'?t|dont|never|no|not|without|avoid|stop|only|just|read-?only)\\b", gl) \
                else _jd.jev_choice("D1_mode", g)
        except Exception:
            _jm = None
        if _jm in ("direct", "orchestrate"):
            return {"mode": _jm, "action": "approve" if is_approval(gl) else ("orchestrate" if _jm == "orchestrate" else "do"),
                    "scoped": bool(_SCOPED.search(gl)) or "nothing else" in gl,
                    "forbid": sorted(set(forb)), "reason": "Jev mode: local decider", "source": "jev"}
    # Engine-first (smart) — but ALWAYS fall back to the deterministic net if it fails.
    if engine is not None:''', "_jd.jev_choice(\"D1_mode\"")
# D2 — dispatcher.route
edit("orchestrator/dispatcher.py", '''            try:
                import semantic_router
                sem = semantic_router.classify(text)
            except Exception:
                sem = None''', '''            try:   # P4e: Jev mode — local decider for specialist + read/change; fallback = the semantic router
                import jev_decider as _jd
                _ja = _jd.jev_choice("D2_agent", text)
                _jr = _jd.jev_choice("D2_action", text) if _ja else None
                if _ja and _jr:   # co-owners from the deterministic keyword rules (the local decider picks the lead)
                    _co = [a for a in self.classify(text) if a != _ja]
                    sem = {"agents": [_ja] + _co, "action": _jr, "why": "Jev mode: local decider"}
            except Exception:
                sem = None
            if sem is None:
                try:
                    import semantic_router
                    sem = semantic_router.classify(text)
                except Exception:
                    sem = None''', "_jd.jev_choice(\"D2_agent\"")
# D4 — QA recommendation
edit("server/api_v2.py", '''                import approvals as _ap
                verdict = projects._engine(''', '''                import approvals as _ap
                try:   # P4e: Jev mode decides yes/no locally; fallback = the engine prompt below
                    import jev_decider as _jd
                    _jq = _jd.jev_choice("D4_qa", goal)
                except Exception:
                    _jq = None
                verdict = '{"recommend": %s, "why": "Jev mode: local decider"}' % ("true" if _jq == "yes" else "false") if _jq else projects._engine(''', "_jd.jev_choice(\"D4_qa\"")
# D9 — new agent nature
edit("server/agents_registry.py", '''            obj = _safe_json_obj(raw)
            if obj:
                role = obj.get("role") or role
                nature = obj.get("nature") or nature''', '''            obj = _safe_json_obj(raw)
            if obj:
                role = obj.get("role") or role
                nature = obj.get("nature") or nature
            try:   # P4e: Jev mode decides technical/operational locally (fallback = the engine's answer above)
                import jev_decider as _jd
                _jn = _jd.jev_choice("D9_nature", description)
                if _jn:
                    nature = _jn
            except Exception:
                pass
            if obj:''', "_jd.jev_choice(\"D9_nature\"")
# mode setting routes
edit("server/api_v2.py", '''    @r.get("/secrets/relay-pubkey")''', '''    @r.get("/settings/decider-mode")
    def decider_mode_get():
        """P4e: Normal (LLM) / Jev mode (local decider). Default normal."""
        import jev_decider as jd
        return {"mode": jd.get_mode(), "ready": (jd.ART / "meta.json").is_file()}

    @r.post("/settings/decider-mode")
    def decider_mode_set(body: dict | None = None):
        import jev_decider as jd
        m = str((body or {}).get("mode", "")).lower()
        if m not in jd.MODES:
            return {"error": f"mode must be one of {jd.MODES}", "mode": jd.get_mode()}
        if m == "jev" and not (jd.ART / "meta.json").is_file():
            return {"error": "the local decider is not trained yet", "mode": jd.get_mode()}
        return {"mode": jd.set_mode(m), "ready": True}

    @r.get("/secrets/relay-pubkey")''', "/settings/decider-mode")
