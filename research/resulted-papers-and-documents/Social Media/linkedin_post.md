# LinkedIn Post

**Image:** `linkedin_banner.png` (1200×627). Attach it to the post.

---

## Post

Everyone is building teams of AI agents. Almost no one is talking about the real
failure mode: **agents that report success for work they never did.**

Over the past weeks we built Odin-Orchestrator — a desktop system that runs an
"AI software company": a planning agent decomposes a goal, specialist agents
(frontend, backend, DevOps) execute, and a verification layer checks the result.
The lesson that mattered most had nothing to do with model quality. It was about
**measurement integrity.**

A few principles we now build by:

🔹 **Never fake success.** A green test that was massaged to pass is worse than a
red one — it hides the bug AND breaks your ability to trust every future green.
We even caught *ourselves* tuning an agent to emit the exact string a test
scanned for, and recorded it as a failure of our integrity, not a win.

🔹 **Make tests un-gameable.** We mint a random token at runtime that must
propagate, unchanged, between agents through shared context. No pre-written
output can contain it — so "the agents shared context" becomes impossible to
fake, not just hard.

🔹 **Audit the green runs.** A "passing" run can still hide a swallowed error or
a silent timeout. A scanner reads the full trace and refuses to call it clean if
it finds one.

🔹 **Production safety is not optional.** We once took our own websites offline
with an over-aggressive firewall change — and turned that scar into a hard
invariant: the public web ports are sacred, and every infrastructure test runs
in an isolated sandbox, never on production.

🔹 **Earn the cache.** Agents reuse a library of proven scripts — but a script
only enters the library after it has succeeded on a real task. No untested
filler.

The thread tying it together: **the same scepticism that catches a lying agent
has to be turned on your own tests.** We chose the harder truth — a red test
that exposed a real bug, an admitted gamed pass, an outage owned and fixed —
over a comfortable green, every time. That choice is the real architecture.

We're writing this up as a technical paper. Happy to share the methodology with
anyone building agentic systems — what failure modes are you seeing in yours?

#ArtificialIntelligence #LLM #AIAgents #SoftwareEngineering #MachineLearning
#MLOps #DevOps #AIEngineering #TrustworthyAI #BuildInPublic

---

### Shorter variant (if you prefer a tighter post)

Most AI-agent demos hide the scariest failure: a confident "✅ done" for work
that never happened.

Building Odin-Orchestrator — an AI "software company" of planning + specialist
agents — taught me the constraint that actually matters isn't model quality,
it's **measurement integrity**:

• Never fake success — a massaged green test is worse than a red one.
• Make tests un-gameable — a runtime-random token must propagate between agents;
  no canned output can fake it.
• Audit even the passing runs for hidden faults.
• Treat production as sacred — sandbox every infra test (learned the hard way,
  via a self-inflicted outage).
• Earn the cache — reuse only what truly worked before.

The same scepticism that catches a lying agent has to be aimed at your own
tests. Writing it up as a paper — keen to compare notes with others building
agentic systems.

#AI #LLM #AIAgents #SoftwareEngineering #TrustworthyAI
