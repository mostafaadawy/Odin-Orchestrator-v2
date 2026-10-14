// WEB: embed the live-meeting asset (served by the brain at /meeting_monitor.html) INSIDE the app as a
// platform-view iframe, so it shows in an in-app dialog (NOT a browser tab) — identical to desktop.
// Only imported on web via conditional import (mirrors speech_web.dart).
import 'dart:html' as html;
import 'dart:ui_web' as ui_web;

bool get canOpenMonitor => true;

final Set<String> _registered = {};

/// The LOCAL brain that serves the meeting asset (/meeting_monitor.html + /meeting/*). On web the brain
/// is the owner's local desktop backend — reachable from the browser at localhost:8000 (or an override in
/// localStorage['odin.base']). We must NOT use a relative URL: the Flutter web app is served from a
/// different origin (e.g. :8080 or the deployed web), so a relative path would 404. Absolute brain URL.
String _brainBase() {
  try {
    final b = html.window.localStorage['odin.base'];
    if (b != null && b.isNotEmpty) return b;
  } catch (_) {}
  return 'http://localhost:8000';
}

/// The absolute brain base (localhost:8000 or localStorage override) — used to build report/export URLs.
String brainBase() => _brainBase();

/// Open a report/export URL from the brain (PDF/DOCX/MD/PPTX) in a new tab (web).
void openReport(String url) {
  try { html.window.open(url, '_blank'); } catch (_) {}
}

/// Registers (once) an <iframe> view for this project's monitor and returns its viewType,
/// to be shown via HtmlElementView inside a dialog. Loads the asset from the BRAIN (absolute URL).
String registerMonitor(String pid) {
  final vt = 'meeting-monitor-$pid';
  if (!_registered.contains(vt)) {
    ui_web.platformViewRegistry.registerViewFactory(vt, (int _) {
      final el = html.IFrameElement()
        ..src = '${_brainBase()}/meeting_monitor.html?pid=${Uri.encodeComponent(pid)}'
        ..style.border = 'none'
        ..style.width = '100%'
        ..style.height = '100%'
        ..allow = 'microphone; autoplay';
      return el;
    });
    _registered.add(vt);
  }
  return vt;
}
