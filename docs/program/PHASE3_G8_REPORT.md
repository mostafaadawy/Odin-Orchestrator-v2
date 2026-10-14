# Phase 3 — G8 (which agent created a file) and the ZERO-COST rule

**Git:** `g8-start` (9b8c541) → **`g8-done` (acf1536)**. CHANGELOG updated. v1 untouched. Paper v1 fingerprint unchanged.

## Your four conditions
| Condition | Proof |
|---|---|
| The migration only ADDS a nullable column; existing rows stay untouched and show "unknown" | The schema diff is the `created_by` column and its comment, nothing else. All existing rows are NULL and labelled "unknown". |
| No existing query, view or test changes behaviour | All views are byte-identical. The code's queries and every view return identical results before and after. No code uses `SELECT * FROM files`. Regression and phase7 tests are green with and without the migration. |
| Reversible; on the cutover list with a backup first | `server/migrations/migrate_g8.sh up\|down\|status` takes a full `pg_dump -Fc` backup before either direction. After `down`, the schema and data are exactly as before. It is listed under P8-4. |
| Every audit finding names the creating agent when known | Every finding carries `created_by` (for duplicates, one entry per copy). The audit log and the notification text also name the creator. |

## How the creator is recorded
- **Agent Write/Edit tools:** a hook after each write records the agent for a NEW file. It never blocks and prints nothing.
- **Approved proposals:** the proposal's agent is recorded.
- **Middleware door writes:** the writing agent is recorded.
- **Other files made during a member's step** (for example by a shell command) are labelled "inferred from step". This applies only to files that were new to the database.
- **Never changed by:** an edit, a re-index or a move.

## Live run S12 (reported usage $1.14, not charged)
- `code/calc.py` and `code/test_calc.py` → **"Fullstack (project s12-creator-r1, via Write tool)"**.
- The audit finding **misplaced `notes_g8.md`** → **created by Fullstack**.
- Fixed after the live run: the run showed that `agents.json` and `.pyc` files were wrongly inferred. Now only files that were new to the database count, and `__pycache__` is excluded (test S2/S3).
- The run ended NOT_DONE because of the deliberately misplaced file. That is correct.

## R-ZC, zero extra cost: auth check (no key printed)
- **Login:** Claude CLI 2.1.185, logged in with your **Claude Max plan** (billing: subscription).
- **No API key anywhere:** none in the environment, the config or the settings, and no apiKeyHelper. No base URL, Bedrock or Vertex settings.
- **Paid extra usage:** **disabled**.
- **New guard:** every model call is refused if any paid route is configured (test Z1–Z4).
- **Dollar figures** are now recorded as "reported usage, not charged", and the dollar cap logic is removed.
- **Plan usage limits:** the CLI does not show the remaining plan percentage to scripts. Batches now stop as soon as a usage-limit message appears. You can see the exact level in the Claude app's usage page.
