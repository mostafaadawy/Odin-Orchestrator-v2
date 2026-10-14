"""F-11 (owner, 2026-10-12): a project's DELTA over a shared base holds ONLY the differences (lines skipped,
added or changed — settings, keys, steps) plus a POINTER to the shared base. It is never a full copy.

  make(base_text, own_text, base_rel)  -> delta dict {"v":1,"base":rel,"base_sha":..,"ops":[...]}
  apply(base_text, delta)              -> the project's exact text (byte-identical to the original copy)
  write_launcher(path, delta)          -> replaces the project's copy with a small executable delta file
                                          (.py / .sh / .bash / .js CommonJS) that runs the materialized text,
                                          so the project behaves exactly as before.
Each op keeps the base lines it replaces, so if the shared base later changes, every op is re-located by its
own base lines; if that is impossible the delta REFUSES to run (DeltaConflict) instead of running something
different. CLI (used by the .sh / .js launchers):  python3 delta.py materialize-json <root> '<delta json>'"""
from __future__ import annotations
import difflib, hashlib, json, os, pathlib, re, sys

SUPPORTED = (".py", ".sh", ".bash", ".js", ".cjs")
HEADER = "delta over shared capability: {base}"


class DeltaConflict(RuntimeError):
    pass


def _lines(t: str) -> list:
    return (t or "").splitlines(keepends=True)


def _h(line: str) -> str:
    return hashlib.sha256(line.encode("utf-8")).hexdigest()[:16]


def sha(t: str) -> str:
    return hashlib.sha256((t or "").encode("utf-8")).hexdigest()


def make(base_text: str, own_text: str, base_rel: str) -> dict:
    a, b = _lines(base_text), _lines(own_text)
    ops = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag != "equal":
            ops.append({"at": i1, "old": a[i1:i2], "new": b[j1:j2],
                        "before": _h(a[i1 - 1]) if i1 > 0 else None})   # anchor = HASH of the line above, not its text
    return {"v": 1, "base": base_rel, "base_sha": sha(base_text), "ops": ops, "own_sha": sha(own_text)}


def _locate(a: list, op: dict, hint: int) -> int:
    old, before = op["old"], op.get("before")
    def ok(i):
        if a[i:i + len(old)] != old:
            return False
        return (before is None and i == 0) or (before is not None and i > 0 and _h(a[i - 1]) == before)
    if 0 <= hint <= len(a) and ok(hint):
        return hint
    for d in range(1, len(a) + 1):        # nearest match to the expected place
        for i in (hint - d, hint + d):
            if 0 <= i <= len(a) and ok(i):
                return i
    raise DeltaConflict(f"the shared base changed where this delta applies (op at base line {op['at'] + 1})")


def apply(base_text: str, delta: dict) -> str:
    a = _lines(base_text)
    exact = sha(base_text) == delta.get("base_sha")
    out, pos, shift = [], 0, 0
    for op in delta.get("ops", []):
        i = op["at"] if exact else _locate(a, op, op["at"] + shift)
        if i < pos:
            raise DeltaConflict("delta ops overlap after the base changed")
        out += a[pos:i] + op["new"]
        pos = i + len(op["old"])
        shift = i - op["at"]
    out += a[pos:]
    text = "".join(out)
    if exact and delta.get("own_sha") and sha(text) != delta["own_sha"]:
        raise DeltaConflict("delta does not reproduce the project's file")
    return text


def materialize(delta: dict, root) -> str:
    base = pathlib.Path(root) / "workspace" / delta["base"]
    if not base.is_file():
        raise DeltaConflict(f"shared base {delta['base']} not found")
    return apply(base.read_text(encoding="utf-8"), delta)


def size_of_changes(delta: dict) -> int:
    return sum(len(o["old"]) + len(o["new"]) for o in delta.get("ops", []))


def launcher(ext: str, delta: dict) -> str:
    js = json.dumps(delta, ensure_ascii=False)
    h = HEADER.format(base=delta["base"])
    if ext == ".py":
        return (f"# {h} — F-11: this file stores ONLY the differences\n"
                f"_ODIN_DELTA = {js}\n"
                "import pathlib as _odp, sys as _ods\n"
                "_odr = next(d for d in _odp.Path(__file__).resolve().parents if (d / 'server' / 'delta.py').is_file())\n"
                "_ods.path.insert(0, str(_odr / 'server')); import delta as _odin_delta\n"
                "exec(compile(_odin_delta.materialize(_ODIN_DELTA, _odr), __file__, 'exec'))\n")
    if ext in (".sh", ".bash"):
        q = js.replace("'", "'\"'\"'")
        return ("#!/usr/bin/env bash\n"
                f"# {h} — F-11: this file stores ONLY the differences\n"
                f"_ODIN_DELTA='{q}'\n"
                '_odr="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; while [ "$_odr" != / ] && [ ! -f "$_odr/server/delta.py" ]; do _odr="$(dirname "$_odr")"; done\n'
                '_odcode="$(python3 "$_odr/server/delta.py" materialize-json "$_odr" "$_ODIN_DELTA")" || exit 97\n'
                'eval "$_odcode"\n')
    if ext in (".js", ".cjs"):
        return (f"// {h} — F-11: this file stores ONLY the differences\n"
                f"const _ODIN_DELTA = {js};\n"
                "const _odp = require('path'), _odf = require('fs'); let _odr = __dirname;\n"
                "while (_odr !== _odp.dirname(_odr) && !_odf.existsSync(_odp.join(_odr, 'server', 'delta.py'))) _odr = _odp.dirname(_odr);\n"
                "const _odc = require('child_process').execFileSync('python3', [_odp.join(_odr, 'server', 'delta.py'), 'materialize-json', _odr, JSON.stringify(_ODIN_DELTA)]).toString();\n"
                "module.exports = (new Function('require', 'module', 'exports', '__filename', '__dirname', _odc + '\\n;return module.exports;'))(require, module, module.exports, __filename, __dirname);\n")
    raise ValueError(f"no executable delta for {ext}")


def supported(path, text: str = "") -> str:
    """'' when a true executable delta is possible for this file; otherwise the reason."""
    ext = pathlib.Path(path).suffix.lower()
    if ext not in SUPPORTED:
        return f"{ext or 'this file type'} cannot run as a delta"
    if ext in (".js", ".cjs") and re.search(r"^\s*(import\s|export\s)", text or "", re.M):
        return "ES-module JavaScript cannot run as a delta"
    return ""


def read_delta(path) -> dict | None:
    t = pathlib.Path(path).read_text(encoding="utf-8", errors="replace")
    m = re.search(r"_ODIN_DELTA\s*=\s*'?(\{.*\})'?\s*;?\s*$", t, re.M)
    if not m:
        return None
    raw = m.group(1).replace("'\"'\"'", "'")
    try:
        return json.loads(raw)
    except Exception:
        return None


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "materialize-json":
        try:
            sys.stdout.write(materialize(json.loads(sys.argv[3]), sys.argv[2]))
        except DeltaConflict as e:
            print(f"[Odin delta] REFUSED: {e}", file=sys.stderr); sys.exit(97)
    else:
        print(__doc__); sys.exit(2)
