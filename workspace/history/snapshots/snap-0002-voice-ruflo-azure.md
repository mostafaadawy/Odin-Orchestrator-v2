# Snapshot: snap-0002-voice-ruflo-azure

**Created (UTC):** 2026-06-21T00:00:00Z
**By:** CTO Brain
**Reason:** Restore point after voice extraction, Ruflo comparison, and Azure procedure.

## What changed since snap-0001
- Added `voice/` — dependency-free EN+AR voice module (Kokoro TTS reused; local Whisper STT;
  Arabic TTS; service + frontend hook). `voice/VOICE-ANALYSIS.md`, `voice/README.md`.
- Added `RUFLO-COMPARISON.md` — sourced technical comparison + adopt/adapt/ignore verdicts.
- Added `runbooks/azure-secure-connection.md` — strict dynamic-IP procedure.
- Added `PENDING.md` — Brain↔agent connection, mobile dispatcher, end-to-end voice.
- Updated `rules/core-rules.md` (§5.1 Azure, §6.2–6.3 voice + no-mostafa-app rule, ADR-004/005/006).
- Updated `infra/azure/connection.profile.json` (procedure + folder mapping + automation policy).
- Updated history + dashboard state (progress 45%).

## To revert here
Follow `runbooks/revert.md` (a pre-revert snapshot is taken first, so this is reversible).
