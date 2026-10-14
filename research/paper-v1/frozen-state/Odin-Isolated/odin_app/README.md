# Odin App — Phase 2 (Flutter: web + Android + iOS)

Companion app for **Odin Orchestrator**. One Dart codebase, three targets. It is a pure **client of
the Phase‑1 contract** (`ANCHOR_CONTRACT.md`) plus the existing project/chat API — no orchestration
or deploy code lives here. Because it only talks to the contract, pointing it at the **deployed
anchor** later (Phase 3) is a one‑line base‑URL change.

## What it does
- **Projects** — lists every project (`GET /api/v1/projects`), on‑click refresh.
- **Chat (on‑demand)** — ask any project a question (`POST /api/v1/p/{id}/ask`); answers grounded in
  that project's brief + shared context. Loads on click, not constant polling.
- **Anchor** — the live status page: counts + the full requests feed
  (`GET /anchor/v1/admin/counts`, `GET /anchor/v1/admin/requests`), on‑click refresh, plus a form to
  **send an external request** (`POST /anchor/v1/requests`) and watch its lifecycle.
- **Notifications** — when a refresh reveals newly `finished`/`failed` Anchor requests, the app raises
  a local notification on mobile and an in‑app banner on web (conditional import → web still builds).
- **Settings** — base URL + the two API keys (`ODIN_API_KEY` for `/api/v1`, `ANCHOR_API_KEY` for
  `/anchor/v1`), with a "Test connection" button. Persisted with `shared_preferences`.

## One‑time setup (on your Mac, needs the Flutter SDK)
The `lib/`, `pubspec.yaml`, etc. are committed here. Generate the native platform folders, then run:

```bash
cd /Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Isolated/odin_app

# 1) generate web/, android/, ios/ scaffolding WITHOUT touching our lib/
flutter create . --platforms web,android,ios --project-name odin_app --org com.odin
git checkout -- lib/        # restore our entry point if flutter regenerated lib/main.dart

# 2) install packages
flutter pub get

# 3) run it
flutter run -d chrome       # web
# flutter run -d <android-device-id>   # Android (flutter devices to list)
# flutter run -d <ios-device-id>       # iOS (needs Xcode)
```

## First run
1. Start the Odin backend locally (so `http://localhost:8000` serves `/api/v1` and `/anchor/v1`).
2. Open **Settings** in the app → set Base URL (`http://localhost:8000` for web/desktop;
   on a real phone use your Mac's LAN IP, e.g. `http://192.168.1.x:8000`) and the two keys if set in
   `oth/.cred` → **Test connection**.
3. Use **Projects** / **Anchor** tabs.

## Voice (device engine — no models shipped)
Sound + mic use the OS speech engine via `flutter_tts` + `speech_to_text` (works on web, iOS,
Android). For **iOS**, add these to `ios/Runner/Info.plist` (once, after `flutter create`):

```xml
<key>NSMicrophoneUsageDescription</key>
<string>Odin uses the microphone for voice notes and voice chat.</string>
<key>NSSpeechRecognitionUsageDescription</key>
<string>Odin transcribes your speech to chat with the CTO.</string>
<key>NSCameraUsageDescription</key>
<string>Odin uses the camera to send photos in project chat.</string>
<key>NSPhotoLibraryUsageDescription</key>
<string>Odin attaches photos from your library in project chat.</string>
```

## Group chat mode (WhatsApp-style)
Each project chat has a **mode switch — CTO ↔ Group**. "CTO" sends your text to the project's
CTO→team (streamed). "Group" is a shared group thread (same `/scope` pool the desktop, web, your
other devices and the agents use): send **text, camera/photo, files (docx/zip), and voice notes**,
**reply** to any message (long-press), and a **voice note shows its transcript directly underneath**
(server-side speech-to-text via faster-whisper). Audio plays in-bubble.
In chat: the 🔊 toggle reads replies aloud; the 🎤 button dictates into the composer.

## Shared chat pool
The app's company chat (`scope=company`) and project chat (`scope=<pid>`) read/write the **same
`/scope` store the desktop and agents use** — so a message you send from web/mobile persists, comes
back when you change pages, and is the same conversation the desktop sees.

## Contract alignment
Every call this app makes is listed in `ANCHOR_CONTRACT.md`. If an endpoint shape changes there, the
single place to update here is `lib/api/anchor_api.dart`.
