# Web/Mobile Enhanced Voice Feature — Technical Plan (PENDING)

**Status:** Pending — brainstormed and agreed. Implement when Mostafa returns.
**Applies to:** Flutter app only (`odin_app/`) — web build (odin-web) + mobile (iPhone). **Desktop is NOT touched.**
**Accessibility context:** Mostafa has a visual impairment and relies on hearing replies and speaking input. Voice is a core accessibility requirement, not a nice-to-have. Text on screen is always kept as well — audio never replaces the readable text.

This document has two parts:
- **Part A — Voice (TTS speaker + STT mic)** — the main feature.
- **Part B — Mobile keyboard dismissal / input UX** — a separate, HIGH-PRIORITY blocker that must be fixed alongside (or before) Part A.

---

## Part A — Voice feature

### A0. Design decisions already locked (do not re-litigate)
- Everyday voice runs **100% on-device** — no backend, no anchor round-trip, no latency, no load on the Mac brain.
- **English** quality via on-device neural voice is good (near-desktop). **Arabic** will exist and be usable but *not* perfect — this is accepted (~90% of the problem solved).
- The **"enhanced voice via desktop XTTS through the anchor"** idea is **shelved** (far-future maybe). Do NOT build it now.
- **No audio is stored or synced.** The pool keeps only text, exactly as today.
- Desktop voice pipeline (`desktop/src/ChatPanel.jsx`, local `/voice/*` endpoints, Kokoro/XTTS/Whisper) stays **completely untouched**.

### A1. Engines / packages
| Target | Engine | Package | Notes |
|---|---|---|---|
| Web (odin-web) | Kokoro-82M in-browser | `kokoro-js` (npm, Transformers.js) | WebGPU for real-time; WASM (q8) fallback. Model ~80 MB, downloaded once and cached. Same voice family as the desktop English voice. |
| Mobile (iOS/Android) | Kokoro / Piper / VITS on-device | `sherpa_onnx` (pub.dev, k2-fsa) | Offline, on-device. English via Kokoro; Arabic via best available on-device Arabic model (Kokoro if acceptable, else a Piper/VITS Arabic voice). |
| Fallback (both) | Native OS/browser TTS | `flutter_tts` / Web SpeechSynthesis | Graceful degradation only, if the neural model fails to load or the platform can't run it. |

**Integration note (web):** `kokoro-js` is a JS library. In Flutter web it is called through JS interop (a small JS shim loaded in `web/index.html`, invoked via `dart:js_interop`). Plan a thin `WebKokoroTts` wrapper with the same interface as the mobile one.

**Integration note (mobile):** `sherpa_onnx` bundles/loads an ONNX model asset. This adds app size (tens of MB per voice). Decide bundle-vs-download at build time; bundling is simplest for offline reliability.

### A2. Text normalizer (CRITICAL for accessibility — build this first)
The "reads a hash as 'hash symbol blah blah', sounds like a curse" problem is a **text problem, not an engine problem**. Before any text is spoken, run it through a normalizer:
- Strip fenced code blocks and inline code (```` ``` ````, `` ` ``) — either skip entirely or announce "code block" once.
- Remove or translate markdown syntax: `#`, `*`, `_`, `>`, `-`, `|`, table pipes, link brackets → speak the link text, not the URL.
- Skip or shorten raw URLs (don't read character-by-character).
- Collapse emojis / special symbols to nothing or a short word.
- Normalize whitespace, bullets → natural pauses.
- **Language-aware:** detect Arabic vs Latin script per segment so the right voice/locale is used and punctuation is handled correctly.
This normalizer benefits every engine and is the single highest-value piece for the accessibility goal.

### A3. Speaker (TTS) — UX requirements
- **Speaker icon at the TOP of the chat header**, clearly visible, in **every** web/mobile screen: normal mode (`chat_screen.dart` — a toggle already exists here, keep/standardize it) AND chat/WhatsApp mode (`whatsapp.dart` — **currently missing, must be added**).
- **Must not override or displace** existing header items (title, sync spinner, "Copy all", Reload). Place it as an additional icon in the same header row with proper spacing; verify nothing is pushed off-screen on narrow widths.
- Toggle ON → each new incoming reply is spoken via the on-device engine (after the normalizer). Toggle OFF → silent.
- Stop-speaking triggers: new message arrives, user leaves the screen, user taps a stop control.
- Optional per-message **play/stop** affordance (tap a bubble to hear just that one) — nice for re-listening; low priority.
- First time the speaker is enabled: lazy-load the model, show a subtle "preparing voice…" indicator; if load fails, fall back to native TTS and inform quietly.

### A4. Mic (STT) — UX requirements & the confirmed approach
- **Keep the mic button on BOTH web and mobile** (Mostafa's call — removing it on mobile looks inconsistent vs web).
- **Technical reality:** iOS gives **no public API to trigger the keyboard's own dictation mic**. So the button instead calls the **device's native speech engine in-app** — `SFSpeechRecognizer` on iOS / Web Speech API in the browser (the same engines behind keyboard dictation). Recognized text is written into the input field.
- **Language:** provide a small **EN/AR toggle** (or follow the app's current language). Reliable *automatic* spoken-language detection is not available — the recognition locale must be set. Document this clearly; default sensibly (e.g., app language), let the user switch.
- **Fix the existing "mic returns the previous message" bug** in `chat_screen.dart._mic()`: start a fresh recognition session, clear the partial buffer, and replace field content cleanly rather than appending stale `recognizedWords`.
- **Remove the broken path:** in `whatsapp.dart`, the mic currently does `_toggleRecord → _attachBytes → uploadScopeFile → _api()` which is hard-blocked in anchor mode (`"backend is not reachable — this must go through the anchor"`). This record→upload voice-note flow must be removed from the mic button (the mic must never hit the backend). Keep normal file/photo attachments as a separate concern (they have the same anchor-upload limitation — out of scope here).
- Web browsers without STT support (Safari/Firefox): feature-detect and disable/hide the mic gracefully rather than showing a dead button.

### A5. Files likely touched (Part A)
- `odin_app/lib/services/voice.dart` — replace/extend to route TTS through Kokoro (web) / sherpa_onnx (mobile) with native fallback; add the normalizer; add locale handling for STT.
- New: `odin_app/lib/services/tts_kokoro_web.dart`, `tts_sherpa_mobile.dart`, `text_normalizer.dart` (conditional imports by platform).
- `odin_app/lib/screens/whatsapp.dart` — add speaker toggle to header; repoint mic to in-app STT; remove record→upload.
- `odin_app/lib/screens/chat_screen.dart` — standardize speaker toggle; fix `_mic()` stale-buffer bug; EN/AR locale.
- `odin_app/web/index.html` — load the kokoro-js shim (web only).
- `odin_app/pubspec.yaml` — add `sherpa_onnx`; add model assets.
- Desktop, backend, anchor, pool: **no changes.**

### A6. Acceptance criteria (Part A)
- Speaker icon visible and working in normal mode AND chat mode, on web AND mobile; no existing header item displaced/clipped.
- Enabling the speaker reads replies in a natural voice for English; usable (accepted-imperfect) for Arabic; symbols/code are NOT read as nonsense.
- Mic button present on web and mobile; produces correct EN/AR transcription into the input; never calls the backend; no stale "previous message".
- No audio persisted to the pool; desktop unaffected; app still builds for web and iOS.

---

## Part B — Mobile keyboard dismissal & input UX (HIGH PRIORITY BLOCKER)

### B1. The problem (confirmed in code)
On mobile, tapping a text field pops the soft keyboard and it **never dismisses**, covering >1/3 of the screen and blocking the chat — a total blocker. Code audit confirms the app has **none** of the standard dismissal mechanisms: no `keyboardDismissBehavior` on any list, no tap-outside `unfocus()`, no dismiss button, no managed `FocusNode`, and a couple of `autofocus: true` fields that force the keyboard up.

### B2. Standard Flutter solution (apply all)
1. **Scroll-to-dismiss:** set `keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag` on the chat `ListView.builder`s (whatsapp.dart, chat_screen.dart). Dragging/scrolling the conversation dismisses the keyboard — the WhatsApp-style behavior Mostafa expects ("let me scroll and see content").
2. **Tap-outside-to-dismiss:** wrap the screen body in a `TapRegion` (preferred) or `GestureDetector(behavior: HitTestBehavior.translucent, onTap: () => FocusManager.instance.primaryFocus?.unfocus())`. Must be translucent so it does NOT swallow taps on buttons, message bubbles, or the input itself — only "empty"/non-editable taps dismiss.
3. **Proper resize:** ensure `Scaffold.resizeToAvoidBottomInset: true` (default, but verify the layout actually uses it) so the input bar sits **above** the keyboard and the message list resizes rather than being hidden; auto-scroll to bottom when the field gains focus so the latest messages stay visible above the keyboard.
4. **Explicit dismiss button:** add a small **down-chevron / "hide keyboard"** button in the input bar. Tapping it calls `focusNode.unfocus()` (keyboard hides, cursor context kept). Tapping the `TextField` again refocuses → keyboard reopens. Requires giving each chat input a managed `FocusNode` (currently none). Ensure re-open always works after a manual close.
5. **No stray auto-keyboard:** remove needless `autofocus: true` (whatsapp.dart rename dialog line ~105, shell.dart line ~391) unless a field genuinely should auto-open. Only real editable fields may ever summon the keyboard; tapping non-editable areas must not.

### B3. Files likely touched (Part B)
- `odin_app/lib/screens/whatsapp.dart` — list `keyboardDismissBehavior`; body `TapRegion`; input `FocusNode` + dismiss button; review `autofocus`.
- `odin_app/lib/screens/chat_screen.dart` — same treatment for the normal-mode chat input/list.
- `odin_app/lib/screens/shell.dart`, `dashboard.dart`, dialogs, `login.dart`, project fields — audit every `TextField` for focus/dismiss behavior; apply a shared helper (e.g., a `DismissKeyboardOnTap` wrapper + a reusable input-bar widget) so the behavior is consistent everywhere.

### B4. Acceptance criteria (Part B)
- Tapping outside any input (empty area, a message, scrolling the list) dismisses the keyboard.
- The keyboard never covers the chat content; the input bar sits directly above it and the latest messages remain visible.
- A visible dismiss button hides the keyboard on demand; tapping the field reopens it reliably.
- No screen auto-pops the keyboard unless intended.
- Verified on a real iPhone in both normal and chat modes.

---

## Suggested order of implementation
1. **Part B first** (keyboard) — it's a hard blocker and independent of voice.
2. **Part A, text normalizer** — highest accessibility value, engine-independent.
3. **Part A, speaker (TTS)** — add toggle everywhere + wire Kokoro/sherpa with native fallback.
4. **Part A, mic (STT)** — in-app native recognition + EN/AR + remove the broken record→upload.
5. Test on real iPhone + web (Chrome) for both English and Arabic; verify desktop untouched.

## Explicit non-goals
- No changes to desktop, backend, anchor, or the message pool.
- No "enhanced voice via anchor/XTTS" button.
- No storing/syncing of audio.
- Fixing general file/photo attachment-through-anchor is out of scope (separate known issue).
