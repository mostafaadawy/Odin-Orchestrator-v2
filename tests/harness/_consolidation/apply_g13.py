import pathlib
def patch(path, a, b):
    p = pathlib.Path(path); s = p.read_text(); assert s.count(a) == 1, (path, a[:70]); p.write_text(s.replace(a, b))
patch("server/api_v2.py", """    cadence: str = ""             # once | recurring | periodical
""", """    cadence: str = ""             # once | recurring | periodical
    readiness: list | None = None  # G13: intake readiness; a NEEDED new platform -> proposal to strengthen an agent
""")
patch("server/api_v2.py", """                                       periodic=body.periodic, cadence=body.cadence,
                                       identifier=body.identifier)
""", """                                       periodic=body.periodic, cadence=body.cadence,
                                       identifier=body.identifier, readiness=body.readiness)
""")
patch("server/api_v2.py", """        elif a and a.get("kind") == "qa-recommendation":
            # owner accepted""", """        elif a and a.get("kind") == "strengthen":
            import strengthen   # G13: add the skill (additive, logged, reversible)
            return {**(approvals.get(aid) or a), "strengthen": strengthen.apply(aid)}
        elif a and a.get("kind") == "qa-recommendation":
            # owner accepted""")
patch("server/projects.py", """                   periodic: dict | None = None, cadence: str = "", identifier: str = "") -> dict:
""", """                   periodic: dict | None = None, cadence: str = "", identifier: str = "",
                   readiness: list | None = None) -> dict:
""")
patch("desktop/src/views.jsx", """      type: finalType, stack: spec.stack || "", mode: isExisting ? "existing" : "build",
      localPath: isExisting ? (folders[0] || "") : (path || folders[0] || ""),""", """      type: finalType, stack: spec.stack || "", mode: isExisting ? "existing" : "build",
      readiness: spec.readiness || [],   // G13: a needed new platform -> "strengthen agent" proposal
      localPath: isExisting ? (folders[0] || "") : (path || folders[0] || ""),""")
print("patched (create_project hook placed separately)")
patch("server/projects.py", """    # company-level feed entry
    import scopes  # type: ignore
    scopes.sync_up(f"project:{pid}", f"Project created: {name}")
    return proj
""", """    # G13: a platform the intake marked as NEEDED -> propose (never apply) strengthening the builder agent
    if readiness:
        try:
            import strengthen
            strengthen.propose_from_readiness(pid, readiness)
        except Exception:
            pass
    # company-level feed entry
    import scopes  # type: ignore
    scopes.sync_up(f"project:{pid}", f"Project created: {name}")
    return proj
""")
print("hook placed")
