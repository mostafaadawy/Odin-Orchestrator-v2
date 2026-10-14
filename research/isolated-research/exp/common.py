"""Shared measurement helpers: environment snapshot, per-PID CPU/memory, stage time-tags, cost ledger."""
import os, json, time, subprocess, platform, pathlib, datetime
import psutil
ISO = pathlib.Path("/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Isolated")
RES = ISO / "_research" / "results"
REAL = pathlib.Path("/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Orchestrator")

def _sysctl(k):
    try: return subprocess.run(["sysctl", "-n", k], capture_output=True, text=True).stdout.strip()
    except Exception: return ""

def env_snapshot(label=""):
    """M4 environment + competing load. The real Odin server (:8000) and the owner's scheduled SOC agents
    are external load — recorded so their CPU can be separated from test results."""
    procs = []
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cpu = p.cpu_percent(None)
            procs.append(p)
        except Exception: pass
    time.sleep(1.0)
    top = []
    for p in procs:
        try:
            c = p.cpu_percent(None)
            if c > 1.0:
                cmd = " ".join(p.info.get("cmdline") or [])[:120]
                top.append({"pid": p.pid, "name": p.info.get("name"), "cpu_pct": round(c, 1),
                            "is_real_odin": "AiAgentWorkSpace/Odin-Orchestrator" in cmd,
                            "is_isolated": "Odin-Isolated" in cmd})
        except Exception: pass
    top.sort(key=lambda x: -x["cpu_pct"])
    soc_recent = []
    for d in REAL.glob("workspace/projects/*/data/soc/reports/*.md"):
        try:
            if time.time() - d.stat().st_mtime < 3600: soc_recent.append(d.parent.parent.parent.parent.name)
        except Exception: pass
    vm = psutil.virtual_memory()
    return {"label": label, "utc": datetime.datetime.utcnow().isoformat() + "Z",
            "machine": {"cpu": _sysctl("machdep.cpu.brand_string"), "ncpu": psutil.cpu_count(),
                        "ram_gb": round(vm.total / 2**30, 1), "os": platform.mac_ver()[0], "arch": platform.machine()},
            "load": {"loadavg": os.getloadavg(), "cpu_pct_total": psutil.cpu_percent(0.5),
                     "mem_used_pct": vm.percent},
            "competing_top": top[:8],
            "real_odin_cpu_pct": round(sum(t["cpu_pct"] for t in top if t["is_real_odin"]), 1),
            "soc_reports_last_hour": sorted(set(soc_recent))}

class PidMeter:
    """CPU time + share + RSS for a process tree (the experiment's own PID and its children)."""
    def __init__(self, pid=None):
        self.p = psutil.Process(pid or os.getpid())
    def _tree(self):
        out = [self.p]
        try: out += self.p.children(recursive=True)
        except Exception: pass
        return out
    def sample(self):
        cpu = 0.0; rss = 0
        for q in self._tree():
            try:
                t = q.cpu_times(); cpu += t.user + t.system; rss += q.memory_info().rss
            except Exception: pass
        return {"t": time.time(), "cpu_s": cpu, "rss_mb": rss / 2**20}
    def __enter__(self):
        self.a = self.sample(); self.peak = self.a["rss_mb"]; return self
    def __exit__(self, *e):
        self.b = self.sample()
    def result(self):
        wall = self.b["t"] - self.a["t"]; cpu = self.b["cpu_s"] - self.a["cpu_s"]
        return {"wall_s": wall, "cpu_s": cpu, "cpu_share_of_wall": (cpu / wall if wall else 0),
                "cpu_share_of_machine": (cpu / (wall * psutil.cpu_count()) if wall else 0),
                "rss_mb_end": self.b["rss_mb"]}

class Tags:
    """Stage time-tags (request in, queued, pulled, processed, published, callback sent ...)."""
    def __init__(self): self.t = {}
    def tag(self, k): self.t[k] = time.perf_counter(); return self.t[k]
    def spans(self, order):
        return {f"{a}->{b}": self.t[b] - self.t[a] for a, b in zip(order, order[1:]) if a in self.t and b in self.t}

def save(name, obj):
    RES.mkdir(parents=True, exist_ok=True)
    p = RES / name
    p.write_text(json.dumps(obj, indent=1, default=str))
    return str(p)

def cost_add(source, usd, note=""):
    RES.mkdir(parents=True, exist_ok=True)
    with open(RES / "cost_ledger.jsonl", "a") as f:
        f.write(json.dumps({"utc": datetime.datetime.utcnow().isoformat() + "Z", "source": source,
                            "usd": float(usd or 0), "note": note}) + "\n")

def cost_total():
    p = RES / "cost_ledger.jsonl"
    return sum(json.loads(l)["usd"] for l in open(p)) if p.exists() else 0.0
