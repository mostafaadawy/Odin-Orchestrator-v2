import subprocess, time, sys
from playwright.sync_api import sync_playwright
subprocess.run("fuser -k 5197/tcp", shell=True, stderr=subprocess.DEVNULL)
srv = subprocess.Popen(["npx", "vite", "--port", "5197", "--strictPort"], cwd="/home/claude/deskfull", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(4); fails = []
def check(n, c, info=""):
    print(("PASS " if c else "FAIL ") + n + (f"  [{info}]" if info and not c else ""))
    if not c: fails.append(n)
try:
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page()
        pg.goto("http://localhost:5197/harness_p4t.html"); pg.wait_for_timeout(2500)
        t = pg.locator("[data-testid=decider-toggle]").first
        check("1: toggle shows and defaults to Normal (LLM)", t.count() == 1 and "Normal (LLM)" in t.inner_text(), t.inner_text() if t.count() else "")
        t.click(); pg.wait_for_timeout(500)
        check("2: click switches to Jev mode and saves it on the brain; it says SHADOW (the LLM decides) until the owner's labels", "Jev mode (shadow: LLM decides)" in t.inner_text() and pg.evaluate("window.__srv.mode") == "jev", t.inner_text())
        pg.evaluate("window.__mount()"); pg.wait_for_timeout(500)
        t2 = pg.locator("[data-testid=decider-toggle]").nth(1)
        check("3: a fresh window reads the saved mode (Jev) from the brain", "Jev mode" in t2.inner_text(), t2.inner_text())
        t.click(); pg.wait_for_timeout(500)
        check("4: click again returns to Normal (LLM)", "Normal (LLM)" in t.inner_text() and pg.evaluate("window.__srv.mode") == "normal")
        pg.evaluate("window.__srv.trained = false"); t.click(); pg.wait_for_timeout(500)
        check("5: when the brain refuses Jev (decider not trained), the toggle stays on Normal", "Normal (LLM)" in t.inner_text() and pg.evaluate("window.__srv.mode") == "normal", t.inner_text())
        pg.evaluate("window.__srv.trained = true; window.__srv.authority = 'live'"); pg.evaluate("window.__mount()"); pg.wait_for_timeout(500)
        t3 = pg.locator("[data-testid=decider-toggle]").nth(2); t3.click(); pg.wait_for_timeout(500)
        check("6: only with authority 'live' (after the owner's labels) does it say the local decider decides", "Jev mode (local decider)" in t3.inner_text(), t3.inner_text())
        b.close()
finally:
    srv.terminate()
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
