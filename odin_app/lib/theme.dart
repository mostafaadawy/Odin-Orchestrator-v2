import 'package:flutter/material.dart';

/// Odin design tokens — mirrors desktop/src/theme.css exactly so the app looks
/// like the dashboard, not a generic Material app.
class Odin {
  static const bg = Color(0xFF08090F); // v2
  static const bg2 = Color(0xFF0E1020);
  static const panelSolid = Color(0xFF15172A);
  static const panel = Color(0xB8171533); // v2: violet-tinted glass
  static const stroke = Color(0x14FFFFFF); // .08
  static const strokeStrong = Color(0x29FFFFFF); // .16
  static const txt = Color(0xFFE8ECF6);
  static const txtDim = Color(0xFF9AA4BF);
  static const txtFaint = Color(0xFF5F6885);
  static const brand = Color(0xFF8F7CFF); // v2 accent: violet
  static const brand2 = Color(0xFF38E8C6); // v2 accent: mint
  static const accent = Color(0xFFFF8FD1); // v2 accent: rose
  static const danger = Color(0xFFFF6B81);
  static const ok = Color(0xFF4BE3A0);
  static const warn = Color(0xFFFFCE6B);

  // role colors
  static const frontend = Color(0xFF5AD1FF);
  static const backend = Color(0xFFB07CFF);
  static const devops = Color(0xFFFFB15A);
  static const security = Color(0xFFFF6B81);
  static const qa = Color(0xFF4BE3A0);
  static const database = Color(0xFF6C8CFF);
  static const generic = Color(0xFF9AA4BF);

  static const radius = 16.0;

  static Color role(String kind) {
    switch (avatarKey(kind)) {
      case 'cto':
        return brand2;
      case 'frontend':
        return frontend;
      case 'backend':
        return backend;
      case 'devops':
        return devops;
      case 'security':
        return security;
      case 'qa':
        return qa;
      case 'database':
        return database;
      default:
        return generic;
    }
  }


  // v2: descriptive agent identity — icon + colour from what the agent DOES (its name/role words), so agents are
  // recognisable at a glance (mirrors desktop/src/ui.jsx agentLook). Role kinds (frontend/backend/…) still win.
  static const List<List<Object>> _looks = [
    [r'\b(cto|chief|brain|lead engineer)\b', '🧭', 0xFF38E8C6],
    [r'intrusion|threat|sentinel|soc\b|siem|detection', '🛡️', 0xFFFF6B81],
    [r'purple|red.?team|pentest|attack', '🎯', 0xFFC77DFF],
    [r'vulnerab|patch|cve', '🩹', 0xFFFF8C5A],
    [r'identity|access|iam|auth', '🔑', 0xFFFFD166],
    [r'complian|baseline|policy|governance|config', '📋', 0xFF4CC9F0],
    [r'recover|resilien|backup|continuity|disaster', '♻️', 0xFF4BE3A0],
    [r'incident|respon|alert', '🚨', 0xFFFF4D6D],
    [r'secur', '⛨', 0xFFFF6B81],
    [r'devops|cloud|infra|deploy|kubern|docker|ops\b', '☁️', 0xFFFFB15A],
    [r'\bqa\b|test|review|quality', '✅', 0xFF4BE3A0],
    [r'front|\bui\b|ux|web', '🖥️', 0xFF5AD1FF],
    [r'back.?end|api|full.?stack|server', '⚙️', 0xFFA78BFA],
    [r'database|\bdb\b|sql|data eng', '🗄️', 0xFF6C8CFF],
    [r'analytic|insight|metric|report|bi\b|dashboard', '📊', 0xFF3A86FF],
    [r'sales|crm|hubspot|lead|deal', '🤝', 0xFFFF9F1C],
    [r'email|klaviyo|newsletter|campaign|marketing', '✉️', 0xFFFF8FD1],
    [r'content|creator|writer|copy|poster|social|post', '✍️', 0xFFF472B6],
    [r'transcri', '📝', 0xFF2EC4B6],
    [r'audio|voice|capture|meeting|zoom|call', '🎙️', 0xFF00B4D8],
    [r'fulfil|shipping|easypost|veeqo|order|logistic|warehouse', '📦', 0xFFF4A261],
    [r'amazon|product|catalog|listing', '🛒', 0xFFFFBE0B],
    [r'notif|reminder|schedul|periodic', '🔔', 0xFFFFD166],
    [r'research|scien|paper', '🔬', 0xFF90E0EF],
    [r'translat|language', '🌐', 0xFF8ECAE6],
    [r'finance|account|invoice|billing|payment', '💳', 0xFF52B788],
    [r'support|customer|help', '💬', 0xFF80ED99],
  ];
  static (String, Color) agentLook(String? name, String kind) {
    final k = avatarKey(kind);
    final n = name ?? '';
    if (k != 'generic' && !RegExp(r'security|analytic', caseSensitive: false).hasMatch(n)) return (roleGlyph(kind), role(kind));
    for (final l in _looks) {
      if (RegExp(l[0] as String, caseSensitive: false).hasMatch(n)) return (l[1] as String, Color(l[2] as int));
    }
    return (roleGlyph(kind), role(kind));
  }

  static String roleGlyph(String kind) {
    switch (avatarKey(kind)) {
      case 'cto':
        return '🧭';
      case 'frontend':
        return '▦';
      case 'backend':
        return '❮❯';
      case 'devops':
        return '☁';
      case 'security':
        return '⛨';
      case 'qa':
        return '✓';
      case 'database':
        return '▤';
      default:
        return '✦';
    }
  }

  static String avatarKey(String? a) {
    const known = {'cto', 'frontend', 'backend', 'devops', 'security', 'qa', 'database', 'generic'};
    final k = (a ?? 'generic').toLowerCase();
    if (k == 'project cto' || k == 'cto brain') return 'cto';
    return known.contains(k) ? k : 'generic';
  }

  static Color anchorStatusColor(String s) {
    switch (s) {
      case 'queued':
        return brand2;
      case 'sent_to_local':
      case 'processing':
      case 'response_received':
      case 'webhook_sent':
        return brand;
      case 'ack_pending':
        return warn;
      case 'acknowledged':
      case 'finished':
        return ok;
      case 'failed':
        return danger;
      case 'cancelled':
        return txtFaint;
      default:
        return txtDim;
    }
  }

  static ThemeData theme() {
    final base = ThemeData(brightness: Brightness.dark, useMaterial3: true);
    return base.copyWith(
      scaffoldBackgroundColor: bg,
      colorScheme: const ColorScheme.dark(
        primary: brand,
        secondary: brand2,
        tertiary: accent,
        surface: panelSolid,
        error: danger,
      ),
      appBarTheme: const AppBarTheme(backgroundColor: Colors.transparent, foregroundColor: txt, elevation: 0),
      snackBarTheme: const SnackBarThemeData(backgroundColor: panelSolid, contentTextStyle: TextStyle(color: txt)),
      floatingActionButtonTheme: const FloatingActionButtonThemeData(backgroundColor: brand, foregroundColor: Color(0xFF0B0B16)),
      progressIndicatorTheme: const ProgressIndicatorThemeData(color: brand2),
      textTheme: base.textTheme.apply(bodyColor: txt, displayColor: txt),
      dividerColor: stroke,
      iconTheme: const IconThemeData(color: txtDim),
    );
  }

  /// The full app background gradient (mirrors body radial-gradients).
  static BoxDecoration get bgDecoration => const BoxDecoration(
        // v2: deep indigo base with a violet glow top-left and a mint glow bottom-right
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF1A1440), Color(0xFF0C0D1F), Color(0xFF08090F), Color(0xFF07201E)],
          stops: [0.0, 0.35, 0.7, 1.0],
        ),
      );
}

/// Project type taxonomy — mirrors TYPE_META in views.jsx.
class TypeMeta {
  final String key;
  final String label;
  final String icon;
  final String group; // tech | operational
  const TypeMeta(this.key, this.label, this.icon, this.group);
}

const List<TypeMeta> kTypeMeta = [
  TypeMeta('web', 'Web application', '🌐', 'tech'),
  TypeMeta('mobile', 'Mobile application', '📱', 'tech'),
  TypeMeta('desktop', 'Desktop application', '🖥️', 'tech'),
  TypeMeta('deployment', 'Deployment', '🚀', 'tech'),
  TypeMeta('security', 'Security', '🛡️', 'tech'),
  TypeMeta('scripting', 'Scripting / Automation', '🧩', 'tech'),
  TypeMeta('integration', 'Integration / API', '🔌', 'tech'),
  TypeMeta('embedded', 'Embedded / Firmware', '🔧', 'tech'),
  TypeMeta('gaming', 'Game', '🎮', 'tech'),
  TypeMeta('xr', 'XR (AR / VR)', '🕶️', 'tech'),
  TypeMeta('ai_ml', 'AI / ML', '🧠', 'tech'),
  TypeMeta('data', 'Data / Analytics', '📊', 'tech'),
  TypeMeta('marketing', 'Marketing', '📈', 'operational'),
  TypeMeta('email', 'Email specialist', '✉️', 'operational'),
  TypeMeta('content', 'Content creator', '✍️', 'operational'),
  TypeMeta('support', 'Customer support', '💬', 'operational'),
  TypeMeta('sales', 'Sales / Outreach', '🤝', 'operational'),
  TypeMeta('social', 'Social media', '📣', 'operational'),
  TypeMeta('fulfillment', 'Fulfillment Provider', '📦', 'operational'),
];

TypeMeta? typeByKey(String? k) {
  for (final t in kTypeMeta) {
    if (t.key == k) return t;
  }
  return null;
}
