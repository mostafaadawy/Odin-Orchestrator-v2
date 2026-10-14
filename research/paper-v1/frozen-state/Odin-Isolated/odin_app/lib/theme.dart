import 'package:flutter/material.dart';

/// Odin design tokens — mirrors desktop/src/theme.css exactly so the app looks
/// like the dashboard, not a generic Material app.
class Odin {
  static const bg = Color(0xFF0A0C12);
  static const bg2 = Color(0xFF0F1320);
  static const panelSolid = Color(0xFF161B2A);
  static const panel = Color(0xB3161B2A); // rgba(22,27,42,.72)-ish
  static const stroke = Color(0x14FFFFFF); // .08
  static const strokeStrong = Color(0x29FFFFFF); // .16
  static const txt = Color(0xFFE8ECF6);
  static const txtDim = Color(0xFF9AA4BF);
  static const txtFaint = Color(0xFF5F6885);
  static const brand = Color(0xFF6C8CFF);
  static const brand2 = Color(0xFF7AF0D0);
  static const accent = Color(0xFFB07CFF);
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
        secondary: accent,
        surface: panelSolid,
        error: danger,
      ),
      textTheme: base.textTheme.apply(bodyColor: txt, displayColor: txt),
      dividerColor: stroke,
      iconTheme: const IconThemeData(color: txtDim),
    );
  }

  /// The full app background gradient (mirrors body radial-gradients).
  static BoxDecoration get bgDecoration => const BoxDecoration(
        color: bg,
        gradient: RadialGradient(
          center: Alignment(-0.8, -1.1),
          radius: 1.4,
          colors: [Color(0x296C8CFF), Color(0x00000000)],
          stops: [0.0, 0.6],
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
