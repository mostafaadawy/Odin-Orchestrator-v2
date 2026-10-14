import intent

FAILS=[]
def check(name, cond):
    print(("PASS " if cond else "FAIL ")+name)
    if not cond: FAILS.append(name)

# ---- CASE 1: "just update the list, nothing else, confirm done" -> DIRECT scoped, no team ----
g1=("i have made many modifications and i deployed it so i need you to update the trigger "
    "script for deploy lists to avoid unrequired deployment next time just update nothing else "
    "and confirm done")
c1=intent.classify_request(g1)
check("case1 mode=direct", c1["mode"]=="direct")
check("case1 scoped=True", c1["scoped"] is True)
r1=intent.requirements_for_run(g1)
check("case1 requirements is ONE item (not the brief)", len(r1)==1)
check("case1 no governance/handoff/helper reqs leaked", not any(w in " ".join(r1).lower() for w in ("governance","hand-off","single-file","veeqo","klaviyo","hubspot","analytics")))

# ---- CASE 2: "no deployment, only diagnosis" -> DIRECT + forbid deploy ----
g2=("believe you don't need to make any deployment there is no need to make any deployment "
    "I only ask for the diagnosis so I need to check the logs using SSH to find the reason "
    "why I get bad request for new users")
c2=intent.classify_request(g2)
check("case2 mode=direct (diagnosis, not build)", c2["mode"]=="direct")
check("case2 forbids deploy", "deploy" in c2["forbid"])

# ---- CASE 3: explicit approval binds (not a re-plan) ----
g3="i need you to update and i approve you to update these lists to avoid unrequired deployment"
c3=intent.classify_request(g3)
check("case3 action=approve", c3["action"]=="approve")
check("case3 mode=direct", c3["mode"]=="direct")

# ---- CASE 4: fake completion without evidence is BLOCKED ----
check("case4 '✅ passed' w/o evidence blocked", intent.accept_done("✅ passed (QA + audit clean)", None)["accepted"] is False)
check("case4 'done' WITH diff evidence accepted", intent.accept_done("done", {"diff":"- old\n+ new"})["accepted"] is True)
check("case4 plain analysis (no claim) not blocked", intent.accept_done("here is my read-only analysis", None)["accepted"] is True)

# ---- guardrail: a REAL multi-part build still orchestrates ----
c5=intent.classify_request("build the full app: frontend, backend and deploy it to the VM")
check("case5 real build -> orchestrate", c5["mode"]=="orchestrate")

# ---- guardrail: a deploy that IS requested is allowed, but 'no db rebase' is vetoed ----
g6="run the project, if there are modified files deploy it and test it, and do not rebase the db"
c6=intent.classify_request(g6)
check("case6 deploy NOT forbidden (owner asked to deploy)", "deploy" not in c6["forbid"])
check("case6 db_rebase forbidden", "db_rebase" in c6["forbid"])
check("case6 mode=orchestrate (real deploy op)", c6["mode"]=="orchestrate")

# ---- guardrail: a plain question is direct ----
c7=intent.classify_request("just need to know are we connected")
check("case7 question -> direct", c7["mode"]=="direct")

print("\nRESULT:", "ALL GREEN" if not FAILS else ("FAILED: "+", ".join(FAILS)))
import sys; sys.exit(1 if FAILS else 0)
