"""Anchor queue + callback + live-sync measurement over REAL HTTP against Odin's anchor stand-in (anchor_remote.py),
started in a throwaway root. Processing is synthetic (fixed), so the timings isolate queue/Anchor/callback overhead.
usage: anchor_exp.py <root>"""
import sys, os, json, time, threading, subprocess, http.server, urllib.request, random, pathlib, statistics as st
root = pathlib.Path(sys.argv[1]).resolve()
if "/_research/tmp/" not in str(root) or not (root / "server").is_dir(): sys.exit("REFUSED: throwaway root required")
sys.path.insert(0, str(pathlib.Path(__file__).parent)); from common import PidMeter, env_snapshot, save
A = "http://127.0.0.1:18191"; CB = "http://127.0.0.1:18192/cb"
def start_anchor():
    p = subprocess.Popen([sys.executable, "server/anchor_remote.py", "--host", "127.0.0.1", "--port", "18191"],
                         cwd=root, stdout=open(root / "anchor.log", "a"), stderr=subprocess.STDOUT)
    for _ in range(100):
        try: urllib.request.urlopen(A + "/anchor/v1/_status", timeout=1); return p
        except Exception: time.sleep(0.1)
    raise SystemExit("anchor did not start")
def call(m, path, body=None):
    d = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(A + path, data=d, method=m, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=30) as x: return json.loads(x.read() or b"{}")
ARR = {}; FAIL = {"rate": 0.0}; rng = random.Random(7)
class H(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        b = json.loads(self.rfile.read(int(self.headers.get("content-length", 0))))
        if rng.random() < FAIL["rate"]:
            self.send_response(500); self.end_headers(); return
        ARR.setdefault(b["request_id"], time.perf_counter()); self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
    def log_message(self, *a): pass
rcv = http.server.ThreadingHTTPServer(("127.0.0.1", 18192), H); threading.Thread(target=rcv.serve_forever, daemon=True).start()
anchor = start_anchor()
out = {"env": env_snapshot("anchor exp")}

def queue_run(M, clients, fail_rate, proc_s=0.0):
    FAIL["rate"] = fail_rate; ARR.clear(); tags = {}
    call("POST", "/anchor/v1/admin/config", {"retry_count": 6, "retry_interval_sec": 0.2, "poll_limit": 5}) if True else None
    lock = threading.Lock(); done_in = threading.Event()
    def client(k):
        for i in range(k, M, clients):
            t_in = time.perf_counter()
            r = call("POST", "/anchor/v1/requests", {"project": "vm-sentinel", "prompt": f"q{i}", "webhook_url": CB})
            with lock: tags[r["request_id"]] = {"in": t_in, "queued": time.perf_counter()}
    def poller():
        idle = 0
        while idle < 40:
            ts = call("GET", "/anchor/v1/poll").get("tasks", [])
            if not ts:
                idle += 1; time.sleep(0.05); continue
            idle = 0
            for t in ts:
                rid = t["id"]; tp = time.perf_counter()
                if proc_s: time.sleep(proc_s)
                tpr = time.perf_counter()
                call("POST", f"/anchor/v1/requests/{rid}/result", {"result": {"answer": "ok"}})
                with lock:
                    tags.setdefault(rid, {}).update({"pulled": tp, "processed": tpr, "published": time.perf_counter()})
    with PidMeter(anchor.pid) as pm:
        t0 = time.perf_counter()
        cs = [threading.Thread(target=client, args=(k,)) for k in range(clients)]; pl = threading.Thread(target=poller)
        [c.start() for c in cs]; pl.start(); [c.join() for c in cs]; pl.join()
        t_main = time.perf_counter()
        # failed callbacks are re-delivered by the anchor's OWN retry sweep (every 30 s) — wait for it
        deadline = time.time() + (95 if fail_rate else 3)
        while len(ARR) < M and time.time() < deadline: time.sleep(0.25)
        t1 = time.perf_counter()
    # final statuses
    sts = [call("GET", f"/anchor/v1/requests/{rid}").get("status") for rid in tags]
    spans = {"in->queued": [], "queued->pulled": [], "pulled->processed": [], "processed->published": [], "published->callback": []}
    tot = []
    for rid, t in tags.items():
        if all(k in t for k in ("in", "queued", "pulled", "processed", "published")) and rid in ARR:
            seq = [t["in"], t["queued"], t["pulled"], t["processed"], t["published"], ARR[rid]]
            for k, a, b in zip(spans, seq, seq[1:]): spans[k].append(b - a)
            tot.append(seq[-1] - seq[0])
    T = sum(tot) or 1
    share = {k: sum(v) / T for k, v in spans.items()}
    return {"M": M, "clients": clients, "webhook_fail_rate_injected": fail_rate, "proc_s": proc_s,
            "callback_success_ratio": len(ARR) / M, "finished_ratio": sts.count("finished") / M,
            "status_counts": {s: sts.count(s) for s in set(sts)},
            "throughput_req_per_s": M / (t_main - t0), "retry_wait_s": t1 - t_main, "stage_share_of_end_to_end": share,
            "e2e_median_ms": st.median(tot) * 1000 if tot else None, "anchor_proc": pm.result()}

runs = []
for rep in range(3):
    for M, cl, fr in ((50, 1, 0.0), (200, 4, 0.0), (200, 4, 0.2)):
        runs.append({"rep": rep, **queue_run(M, cl, fr)})
out["queue"] = runs
# retry path: the anchor schedules failed callbacks; drive its retry loop until all delivered
# ---- live sync (WhatsApp-style mirror): push -> visible propagation, durability across anchor restart ----
sync = []
for i in range(20):
    pool = [{"seq": s, "role": "user", "content": f"m{s}"} for s in range(1, i + 2)]
    t0 = time.perf_counter(); call("POST", "/anchor/v1/sync", {"projects": [{"id": "vm-sentinel"}], "pools": {"vm-sentinel": pool}})
    since = i
    while True:
        r = call("GET", f"/anchor/v1/pool/vm-sentinel?since={since}")
        if r.get("max_seq", 0) >= i + 1: break
    sync.append(time.perf_counter() - t0)
before = call("GET", "/anchor/v1/projects")
anchor.terminate(); anchor.wait(timeout=10)
t_restart = time.perf_counter(); anchor = start_anchor(); restart_s = time.perf_counter() - t_restart
after = call("GET", "/anchor/v1/projects"); pool_after = call("GET", "/anchor/v1/pool/vm-sentinel")
gap_detect = call("GET", "/anchor/v1/pool/vm-sentinel?since=15")
out["sync"] = {"push_to_visible_median_ms": st.median(sync) * 1000, "push_to_visible_p95_ms": sorted(sync)[int(.95 * len(sync))] * 1000,
               "mirror_survives_restart": after.get("projects") == before.get("projects") and len(after.get("projects", [])) > 0,
               "pool_survives_restart": pool_after.get("max_seq") == 20, "stale_flag_after_restart": after.get("stale"),
               "delta_since15_returns": [m["seq"] for m in gap_detect.get("messages", [])]}
anchor.terminate(); rcv.shutdown()
print(save("anchor_exp.json", out))
