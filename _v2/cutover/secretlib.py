"""Shared credential-scan helpers. NEVER prints a value — only key names, paths and counts."""
import io, pathlib, re, tarfile, zipfile
V2 = pathlib.Path(__file__).resolve().parents[2]
WS = V2.parent
NOT_SECRET = {"KLAVIYO_API_REVISION", "KLAVIYO_BASE_URL", "VEEQO_BASE_URL"}
CRED_FILES = (sorted((V2 / "workspace/shared/oth").glob(".cred*"))
              + [V2 / "workspace/projects/odin-external-arms/deploy/anchor/.cred",
                 WS / "Odin-Orchestrator/workspace/shared/oth/.cred",                       # v1: READ only
                 WS / "Odin-Orchestrator/workspace/projects/odin-external-arms/deploy/anchor/.cred"])

def load_values():
    """{value_bytes: key_name} from every known .cred (current, rotation backups, v1) — read only."""
    vals = {}
    for f in CRED_FILES:
        if not f.exists(): continue
        for line in f.read_text(errors="replace").splitlines():
            m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*[:=]\s*(.+)", line)
            if m and m.group(1) not in NOT_SECRET:
                v = m.group(2).strip().strip('"').strip("'")
                if len(v) >= 10 and not v.startswith("http"):
                    vals[v.encode()] = m.group(1)
    return vals

# Method 2: generic secret SHAPES (catches keys that are in no .cred file at all)
PATTERNS = {
    "private-key-block": rb"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "aws-access-key": rb"\bAKIA[0-9A-Z]{16}\b",
    "openai/anthropic-key": rb"\bsk-(?:ant-)?[A-Za-z0-9_\-]{24,}",
    "klaviyo-private-key": rb"\bpk_[A-Za-z0-9]{30,}",
    "hubspot-pat": rb"\bpat-(?:na|eu)[0-9]-[0-9a-f\-]{30,}",
    "easypost-key": rb"\bEZ[AT]K[0-9a-zA-Z]{30,}",
    "github-token": rb"\bgh[pousr]_[A-Za-z0-9]{30,}",
    "slack-token": rb"\bxox[abposr]-[A-Za-z0-9\-]{20,}",
    "google-api-key": rb"\bAIza[0-9A-Za-z_\-]{35}\b",
    "assigned-secret": rb"(?i)\b[A-Z0-9_]*(?:API_KEY|SECRET|PASSWORD|TOKEN)[A-Z0-9_]*\s*[:=]\s*[\"']?(?!<REDACTED)(?![$<{(])[A-Za-z0-9_\-/+=.]{20,}",
}
PATTERNS = {k: re.compile(v) for k, v in PATTERNS.items()}

ARCH = re.compile(r"\.(tgz|tar\.gz|tar|zip|gz|jar|whl|tbz2|tar\.bz2|txz|tar\.xz)$", re.I)

def members(name, data, depth=0):
    """Yield (inner_path, bytes) for every file inside an archive, recursively (depth ≤ 3)."""
    if depth > 3: return
    try:
        if zipfile.is_zipfile(io.BytesIO(data)):
            z = zipfile.ZipFile(io.BytesIO(data))
            for i in z.infolist():
                if i.is_dir(): continue
                b = z.read(i); p = f"{name}!{i.filename}"
                yield p, b
                if ARCH.search(i.filename): yield from members(p, b, depth + 1)
            return
        t = tarfile.open(fileobj=io.BytesIO(data), mode="r:*")
        for i in t.getmembers():
            if not i.isfile(): continue
            b = t.extractfile(i).read(); p = f"{name}!{i.name}"
            yield p, b
            if ARCH.search(i.name): yield from members(p, b, depth + 1)
    except Exception as e:
        yield f"{name}!<UNREADABLE:{type(e).__name__}>", b""

def scan_bytes(data, vals):
    """-> (value_key_names, pattern_names)"""
    return ({k for v, k in vals.items() if v in data},
            {n for n, rx in PATTERNS.items() if rx.search(data)})
