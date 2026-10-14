import subprocess, time, json, sys
from playwright.sync_api import sync_playwright
srv = subprocess.Popen(["npx", "vite", "--port", "5199", "--strictPort"], cwd="/home/claude/desk", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(4)
fails = []
def check(n, c):
    print(("PASS " if c else "FAIL ") + n)
    if not c: fails.append(n)
try:
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 900, "height": 900})
        pg.goto("http://localhost:5199/harness.html"); pg.wait_for_timeout(1500)
        pg.get_by_text("Approvals").first.click(); pg.wait_for_timeout(500)
        pg.get_by_text("Approve all safe").click(); pg.wait_for_timeout(500)
        posts = pg.evaluate("window.__posts")
        check("clicking 'Approve all safe' approves NOTHING yet", posts == [])
        panel = pg.locator("[data-testid=approve-all-confirm]")
        t = panel.inner_text()
        check("confirmation lists every non-security proposal with id and project",
              all(s in t for s in ("aaaa11112222", "shop-site", "bbbb33334444", "crm-sync")))
        check("confirmation shows what each changes (file, command)", "form.html" in t and "npm ci" in t)
        check("security alarm is NOT in the list", "ssss55556666" not in t)
        pg.screenshot(path="/home/claude/desk/f33_confirm.png")
        panel.get_by_text("Cancel").click(); pg.wait_for_timeout(300)
        check("Cancel approves nothing", pg.evaluate("window.__posts") == [])
        pg.get_by_text("Approve all safe").click(); pg.wait_for_timeout(300)
        pg.locator("[data-testid=approve-all-confirm]").get_by_text("Confirm").click(); pg.wait_for_timeout(800)
        posts = pg.evaluate("window.__posts")
        approved = sorted(x.split("/approvals/")[1].split("/")[0] for x in posts)
        check("Confirm approves EXACTLY the 2 listed proposals", approved == ["aaaa11112222", "bbbb33334444"])
        check("security alarm still pending", not any("ssss55556666" in x for x in posts))
        b.close()
finally:
    srv.terminate()
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
