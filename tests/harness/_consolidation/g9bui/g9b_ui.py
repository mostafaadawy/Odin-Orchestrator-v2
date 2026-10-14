import subprocess, time, sys
from playwright.sync_api import sync_playwright
srv = subprocess.Popen(["npx", "vite", "--port", "5198", "--strictPort"], cwd="/home/claude/desk", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(4); fails = []
def check(n, c, info=""):
    print(("PASS " if c else "FAIL ") + n + (f"  [{info}]" if info and not c else ""))
    if not c: fails.append(n)
SECRET = "kv_UI_TEST_value_123"
try:
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 900, "height": 900})
        pg.goto("http://localhost:5198/harness_g9b.html"); pg.wait_for_timeout(1500)
        pg.get_by_text("Approvals").first.click(); pg.wait_for_timeout(500)
        form = pg.locator("[data-testid=key-request-form]")
        check("a key request shows the secure key form (not Approve/Reject)", form.count() == 1 and pg.get_by_text("✓ Approve").count() == 0)
        check("the key name is pre-filled from the agent's request", pg.locator("[data-testid=key-name]").input_value() == "KLAVIYO_KEY_BRAND3")
        check("the value field is a hidden password field", pg.locator("[data-testid=key-value]").get_attribute("type") == "password")
        check("Save is disabled until a value is typed", pg.locator("[data-testid=key-save]").is_disabled())
        pg.locator("[data-testid=key-value]").fill(SECRET)
        pg.screenshot(path="/home/claude/desk/g9b_form.png")
        pg.locator("[data-testid=key-save]").click(); pg.wait_for_timeout(700)
        posts = pg.evaluate("window.__posts")
        check("the value goes ONLY to the app's secure endpoint", len(posts) == 1 and posts[0]["url"].endswith("/secrets/project-key"), posts)
        body = posts[0]["body"] if posts else {}
        check("it sends the request id, the NAME and the service", body.get("aid") == "kkkk11112222" and body.get("name") == "KLAVIYO_KEY_BRAND3" and body.get("service") == "klaviyo", body)
        check("no approve call is made for a key request", not any("/approve" in x["url"] for x in posts))
        check("after saving, the value is not on the page any more", SECRET not in pg.content())
        b.close()
finally:
    srv.terminate()
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
