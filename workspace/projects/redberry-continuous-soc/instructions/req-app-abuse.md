# SOC Requirement — App-Abuse Intrusion Detection & Response (owner-added 2026-07-19)

## Problem (owner-reported)
A set of source IPs repeatedly hit the website's **newsletter, sign-in, and signup (incl. 2FA)** input
fields to mass-create members and to **drain the Klaviyo and HubSpot balance/quota**. Owner mitigated the
immediate impact with **CAPTCHA** (working). Remaining need: identify and characterise the actor(s).

## What the SOC must do (standing objective for BehaviorIDS + Investigator + Architect + Enrich/Intel + Reporter)
1. **Profile every source IP** on guest/auth/subscribe/newsletter endpoints from the production nginx logs
   (read-only): request cadence, endpoints, accounts-created fan-out, user-agent rotation, timing regularity.
2. **Separate the owner** (dynamic IP, interactive/admin but benign) from real bad actors — allow-list + the
   interactive-vs-automated behaviour signature — to **minimise false positives**. Owner admin access is NOT
   misbehaviour; do not mix owner with attackers.
3. **Identify & enrich** the flagged IPs: ASN/org/geo, is it new or returning "from the beginning", does it
   rotate/change over time, and find **siblings** (same ASN/subnet/behaviour). Persist profiles across runs so
   recurring actors are recognised.
4. **Report** — the Reporting agent produces a professional, evidence-based report (who, since when, pattern,
   confidence, impact on Klaviyo/HubSpot spend), no fake analysis / no fabricated evidence.
5. **Prepare a practical prevention/response plan** that **NEVER disconnects real customers** — layered:
   keep CAPTCHA, add rate-limit + progressive challenge + honeypot fields, monitor connector spend, and
   block only **confirmed-bad** IPs at the edge/UFW.

## HARD GATE (non-negotiable)
Blocking / prevention is **PREPARED and PROPOSED for the owner to accept or reject** — it is **NEVER
auto-applied**. The SOC surfaces the plan as an approval request; it does not execute blocks itself.
