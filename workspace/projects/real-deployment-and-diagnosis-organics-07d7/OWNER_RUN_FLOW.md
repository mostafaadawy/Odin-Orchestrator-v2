# OWNER'S RUN FLOW — Real Deployment & Diagnosis (Organics)

## THE ONE RULE THAT OVERRIDES EVERYTHING
On each run turn, do ONLY the NEXT single step, then STOP and wait for the owner's answer. NEVER do
several steps in one turn. NEVER put more than one action in an approval. NEVER bundle deploy + database +
report together — that is the #1 thing the owner rejects. Reads run freely (no approval); only a real WRITE
pauses, and only ONE write-question at a time.

## FIRST run turn — do ONLY this:
1) Run `deploy_changes.py scan` (read-only). List the ACTUAL changed files plainly.
2) Ask the SINGLE question: "Deploy these files?" — as ONE approval, nothing else attached.
3) STOP. Do NOT mention/propose the AI report, the database, or the diagnosis yet.

## After the owner answers the DEPLOY question:
- If NO -> ask ONE separate approval: "Update the change-list baseline so it won't flag again?" (they
  deployed manually). Then STOP.
- If YES -> deploy ONLY those files with the EXISTING protocol, nothing new: refresh the firewall by
  REPLACING only the single currently-used port-22 IP (keep 80/443, never open new ports, never close
  active ones), SSH as mostafa, rsync the changed files, build, restart. Report deploy result. Then go to
  the DB step below.

## DATABASE step (only after a YES deploy, and ONLY if a changed file is a schema/seed file):
- Ask ONE separate approval: "Migrate/replace the database?" State the recommendation — recommended ONLY if
  schema/seed actually changed; if none, say it is NOT recommended. YES -> additive migration (no
  destructive rebase unless explicitly told). NO -> skip. If NO schema/seed file changed, do NOT ask at all.
- Then STOP for that answer.

## TEST (after the deploy/DB finish): run the EXISTING post-deploy tests (endpoints + DB checks already
defined — nothing new). Say clearly whether the deploy succeeded.

## DIAGNOSIS (ANNOUNCE, do NOT ask — say "starting the diagnosis"): read-only across EVERY connected agent:
- Email (Klaviyo): a global read, e.g. number of profiles.
- Fulfillment (Veeqo): number of orders; AND the known DELIVERED order — pull its info, feed Veeqo's
  carrier+tracking to the EasyPost operator, get EasyPost's full delivered status, and COMPARE to our DB's
  stored status for that order.
- HubSpot / Analytics / any other connected agent: their read.
EXECUTE every read to completion IN THE SAME TURN and POST the real values (Klaviyo profile count; Veeqo
order count + the delivered order's EasyPost tracking vs our DB status; HubSpot). NEVER end a turn after
only announcing "starting the diagnosis" or "running the reads" — announcing without the results is a
FAILURE. Reply with a CLEAR result: GREEN if everything passed and nothing paused; if something failed,
find and state the exact REASON.

## REPORT — ONLY on a real problem. If everything is green, do NOT write or even propose any change to
AI_DIAGNOSIS_REPORT.md. Touch it ONLY when the diagnosis finds a real problem needing changes.

Never reinvent the protocol — use the existing firewall/SSH/deploy/test flow exactly as already defined.
One gate per turn. Stop and wait. Never bundle.
