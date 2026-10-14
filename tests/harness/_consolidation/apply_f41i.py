import pathlib
p = pathlib.Path("server/api_v2.py"); s = p.read_text()
a = """        import approvals
        if all:
            return {"approvals": approvals.list_for(pid or None)}
        return {"approvals": approvals.list_pending(pid or None)}
"""
b = """        import approvals
        rows = approvals.list_for(pid or None) if all else approvals.list_pending(pid or None)
        # F-41 interim: a key request is answered ONLY on the desktop (secure field). Clients that cannot
        # host that field (the phone) show "enter this key on the desktop" and never send a key.
        for x in rows:
            if x.get("kind") == "key_request":
                x["desktop_only"] = True
                x["detail"] = "Enter this key on the desktop. The phone never sends keys."
        return {"approvals": rows}
"""
assert s.count(a) == 1; s = s.replace(a, b); p.write_text(s); print("ok")
