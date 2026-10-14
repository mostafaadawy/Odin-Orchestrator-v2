import 'package:flutter/material.dart';
import 'theme.dart';

class GlassCard extends StatelessWidget {
  final Widget child;
  final EdgeInsets padding;
  final VoidCallback? onTap;
  const GlassCard({super.key, required this.child, this.padding = const EdgeInsets.all(18), this.onTap});

  @override
  Widget build(BuildContext context) {
    final card = Container(
      padding: padding,
      decoration: BoxDecoration(
        color: Odin.panel,
        borderRadius: BorderRadius.circular(Odin.radius),
        border: Border.all(color: Odin.stroke),
        boxShadow: const [BoxShadow(color: Color(0x73000000), blurRadius: 50, offset: Offset(0, 18))],
      ),
      child: child,
    );
    if (onTap == null) return card;
    return InkWell(borderRadius: BorderRadius.circular(Odin.radius), onTap: onTap, child: card);
  }
}

class Pill extends StatelessWidget {
  final String text;
  final Color? color;
  final Color? borderColor;
  final Widget? leading;
  final VoidCallback? onRemove;
  const Pill(this.text, {super.key, this.color, this.borderColor, this.leading, this.onRemove});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
      decoration: BoxDecoration(
        color: const Color(0x08FFFFFF),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: borderColor ?? Odin.strokeStrong),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (leading != null) ...[leading!, const SizedBox(width: 6)],
          Flexible(
            child: Text(text,
                maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 11, color: color ?? Odin.txtDim)),
          ),
          if (onRemove != null) ...[
            const SizedBox(width: 6),
            InkWell(onTap: onRemove, child: const Icon(Icons.close, size: 12, color: Odin.txtFaint)),
          ],
        ],
      ),
    );
  }
}

class StatusDot extends StatelessWidget {
  final String state; // ok | warn | bad
  final String? label;
  const StatusDot({super.key, this.state = 'ok', this.label});

  @override
  Widget build(BuildContext context) {
    final c = state == 'ok' ? Odin.ok : state == 'warn' ? Odin.warn : Odin.danger;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 9,
          height: 9,
          decoration: BoxDecoration(
            color: c,
            shape: BoxShape.circle,
            boxShadow: [BoxShadow(color: c.withValues(alpha: 0.16), blurRadius: 0, spreadRadius: 4)],
          ),
        ),
        if (label != null) ...[
          const SizedBox(width: 7),
          Flexible(child: Text(label!, style: const TextStyle(fontSize: 12.5, color: Odin.txtDim))),
        ],
      ],
    );
  }
}

class Kpi extends StatelessWidget {
  final String value;
  final String label;
  final Color? color;
  const Kpi(this.value, this.label, {super.key, this.color});
  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(value, style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: color ?? Odin.txt)),
        Text(label, style: const TextStyle(fontSize: 11, color: Odin.txtFaint, letterSpacing: 0.4)),
      ],
    );
  }
}

class SectionTitle extends StatelessWidget {
  final String text;
  final double size;
  const SectionTitle(this.text, {super.key, this.size = 18});
  @override
  Widget build(BuildContext context) =>
      Text(text, style: TextStyle(fontSize: size, fontWeight: FontWeight.w700, color: Odin.txt));
}

/// Role-colored agent avatar. When [active] it shows the working heartbeat ring +
/// glow — animation MEANS the agent is really working (idle = calm), exactly like
/// the desktop.
class Avatar extends StatefulWidget {
  final String kind;
  final bool active;
  final double size;
  const Avatar({super.key, this.kind = 'generic', this.active = false, this.size = 56});
  @override
  State<Avatar> createState() => _AvatarState();
}

class _AvatarState extends State<Avatar> with SingleTickerProviderStateMixin {
  late final AnimationController _c =
      AnimationController(vsync: this, duration: const Duration(milliseconds: 1400))..repeat();

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final c = Odin.role(widget.kind);
    final r = widget.size / 56;
    return SizedBox(
      width: widget.size + 14,
      height: widget.size + 14,
      child: Center(
        child: AnimatedBuilder(
          animation: _c,
          builder: (_, child) {
            return Stack(
              alignment: Alignment.center,
              children: [
                if (widget.active)
                  Container(
                    width: widget.size + (28 * _c.value) * r,
                    height: widget.size + (28 * _c.value) * r,
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(20 * r),
                      border: Border.all(color: c.withValues(alpha: (1 - _c.value) * 0.8), width: 2),
                    ),
                  ),
                Container(
                  width: widget.size,
                  height: widget.size,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(16 * r),
                    border: Border.all(color: Odin.strokeStrong),
                    gradient: LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [c, Color.alphaBlend(c.withValues(alpha: 0.55), Odin.bg)],
                    ),
                    boxShadow: widget.active
                        ? [BoxShadow(color: c.withValues(alpha: 0.5 * _c.value), blurRadius: 26, spreadRadius: 2)]
                        : null,
                  ),
                  child: Center(
                    child: Text(
                      Odin.roleGlyph(widget.kind),
                      style: TextStyle(fontSize: 18 * r, fontWeight: FontWeight.w800, color: Odin.bg),
                    ),
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

class OdinButton extends StatelessWidget {
  final String label;
  final VoidCallback? onPressed;
  final bool primary;
  final IconData? icon;
  const OdinButton(this.label, {super.key, this.onPressed, this.primary = false, this.icon});
  @override
  Widget build(BuildContext context) {
    final child = Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        if (icon != null) ...[Icon(icon, size: 16), const SizedBox(width: 6)],
        Text(label),
      ],
    );
    if (primary) {
      return FilledButton(
        onPressed: onPressed,
        style: FilledButton.styleFrom(backgroundColor: Odin.brand, foregroundColor: Colors.white),
        child: child,
      );
    }
    return OutlinedButton(
      onPressed: onPressed,
      style: OutlinedButton.styleFrom(foregroundColor: Odin.txt, side: const BorderSide(color: Odin.strokeStrong)),
      child: child,
    );
  }
}

class EmptyHint extends StatelessWidget {
  final String text;
  const EmptyHint(this.text, {super.key});
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.all(40),
        child: Center(child: Text(text, style: const TextStyle(color: Odin.txtFaint))),
      );
}
