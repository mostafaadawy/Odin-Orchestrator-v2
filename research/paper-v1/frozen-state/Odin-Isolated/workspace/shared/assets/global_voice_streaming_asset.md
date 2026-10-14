# Global Voice Streaming Asset — Definition & Ownership

A reusable, application-wide asset (managed like the deployment-script / API-power / shared-operational
assets). Owner agent: **Audio Capture Agent** (also exposed as the reusable role **Live Meeting & Voice
Streaming Agent**). Any project needing voice streaming / mic capture / speech-to-text / chunking /
voice-to-report automatically attaches this asset via its owning agent — no other agent duplicates it.

## 1. Global asset definition
Capability: capture authorized microphone / meeting audio, measure sensitivity, cancel noise, detect
language, chunk the stream live, save chunks with metadata, process each chunk, build a final report,
embed it into the project chat pool as Markdown, and export it (MD/DOCX · Arabic/English).

## 2. Source & dependency mapping
- UI (shared, cross-platform): `dashboard/meeting_monitor.html` (served by the brain) — the popup dialogue.
- Backend endpoints: `server/meeting_api.py` → `/meeting/capable|state|clear|chunk|finish|finish_text|view|report|report_all`.
- Transcription: `scopes.transcribe` (faster-whisper/Whisper).
- Report engine (raw, no approval gate): `projects._engine` (Claude CLI) with EN/AR templates.
- Export: `python-docx` (colorful styled DOCX), Markdown, zip for all-four.
- Mobile (native): `odin_app/lib/screens/meeting_sheet.dart` (on-device `speech_to_text`) → anchor command
  `meeting_report` → `local_poller_http.py` → `/meeting/finish_text`.
- Capability gating: `projects.project_has_meeting_asset(pid)` + agent field `asset="meeting_monitor"`.

## 3. Dialogue UI integration plan (web · Flutter · desktop)
- Desktop (React `ChatPanel.jsx`): 🎙 button beside ▶ → in-app modal hosting the asset via iframe.
- Web (Flutter): 🎙 button → Dialog hosting the asset via an iframe platform-view.
- Mobile (Flutter): 🎙 button → native bottom-sheet (`MeetingSheet`) — mic, sensitivity, live chunks.
- Not a browser page — always an in-app popup dialogue. Button shows only when the project owns the asset.

## 4. Voice chunking workflow
Serial capture (never wait for the end) → each chunk transcribed live → per-chunk metadata (below) →
saved → live status shown → on stop, all chunks merged into one report. Boundaries: speaker change,
silence/voice-activity gap, topic change, detected action/decision/risk, language change, max duration.
Saved chunk record: id, start, end, detected language, speaker, raw + cleaned transcript, noise score,
confidence score, main topic, extracted operational points, processing status.

## 5. Noise cancellation & speech refinement rules
Reduce: background noise, duplicate phrases, filler words, broken fragments, side conversations, artifacts,
misheard/low-confidence segments. Never remove: action items, decisions, names, dates, deadlines, product
names, technical terms, commands, service/file/project names (protected-token preservation). Each chunk
carries a confidence level; low-confidence chunks are marked "Chunk confidence low. Content may require
user review." instead of being silently trusted.

## 6. Language detection & bilingual handling rules
Detect the dominant language (Arabic / English / mixed). Mainly-Arabic: keep Arabic + meaningful English
technical terms, drop irrelevant/background English, preserve English names/commands/APIs/file names.
Mainly-English: keep English + meaningful Arabic names/phrases, drop unrelated Arabic noise. Mixed:
preserve both where meaningful; normalize the final report into the user-selected output language without
losing project-critical terms.

## 7. Markdown report embedding behavior
The report is generated inside the dialogue first, then embedded into the active project chat pool as a
normal assistant Markdown message (sender: "Live Meeting & Voice Streaming Agent"), preserving structure.
Available in both places: the dialogue and the chat pool.

## 8. DOCX & MD export behavior (4 outputs)
End-of-session options: Arabic MD, English MD, Arabic DOCX, English DOCX, or generate all four (.zip).
DOCX is clean/professional/colorful/structured (brand-colored headings, shaded section bands, RTL for
Arabic). MD is well-structured and readable. Arabic and English are supported consistently.

## 9. Global asset activation rule
The owning agent auto-attaches this asset whenever a project needs: voice streaming, mic access, meeting
monitoring, audio-to-text, speech refinement, noise filtering, saved chunks, voice-based report
generation, multilingual meeting summaries, post-meeting reports, or audio-session intelligence.

## 10. Agent role enrichment (owner)
The Audio Capture Agent's role is enriched with: source ownership (the files above), asset dependencies,
script references, UI-integration responsibility, cross-platform behavior responsibility, report-output
responsibility, export-options responsibility, and noise-filtering + language-refinement responsibility.
