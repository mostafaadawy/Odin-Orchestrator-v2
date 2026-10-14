import 'package:flutter/material.dart';

import '../theme.dart';

/// v2 identity: the "v2" badge and the "What's new in v2" sheet (shared by web and mobile).
class V2Badge extends StatelessWidget {
  final VoidCallback? onTap;
  const V2Badge({super.key, this.onTap});
  @override
  Widget build(BuildContext context) => InkWell(
        onTap: onTap ?? () => showWhatsNew(context),
        borderRadius: BorderRadius.circular(999),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(999),
            gradient: const LinearGradient(colors: [Odin.brand, Odin.brand2]),
            boxShadow: [BoxShadow(color: Odin.brand.withOpacity(.35), blurRadius: 10)],
          ),
          child: const Text('v2', style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.w900, color: Color(0xFF0B0B16))),
        ),
      );
}

const _news = [
  ['🧠', 'Jev mode — a local decider on the Mac',
    'Normal = the LLM decides, exactly as v1. Jev = a small local model decides closed choices in about 45 ms; low confidence falls back to the LLM. Until your labels are applied Jev runs in shadow (logged only).'],
  ['📱', 'Secure phone approvals',
    'Pair this phone once (Approvals ▸ Pair), compare the fingerprint on the Mac and tap Trust. Approve / Reject is signed on the phone, encrypted for the Mac and usable once — the Anchor only relays ciphertext.'],
  ['🔐', 'Security fixes',
    'The online Anchor now really enforces its key. Web and phone sign in with your Manage login + the one-time code from the Mac (as in v1); no key is inside this app. Keys and passwords were rotated at cutover.'],
  ['📄', 'Paper',
    'Paper v2 (provisional numbers — pending your labels), the paper v1 submission, figures and results tables are in the desktop app\'s Paper tab (the files live on the Mac).'],
  ['🧰', 'One folder, two commands',
    'Everything lives in Odin-Orchestrator-v2: one command for the environment, one for production. Any failed check stops a deploy.'],
];

Future<void> showWhatsNew(BuildContext context) => showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Odin.bg2,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (_) => DraggableScrollableSheet(
        expand: false,
        initialChildSize: .78,
        maxChildSize: .95,
        builder: (ctx, sc) => ListView(
          controller: sc,
          padding: const EdgeInsets.fromLTRB(18, 10, 18, 28),
          children: [
            Center(child: Container(width: 38, height: 4, decoration: BoxDecoration(color: Odin.strokeStrong, borderRadius: BorderRadius.circular(4)))),
            const SizedBox(height: 14),
            const Row(children: [
              Text("What's new in Odin ", style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
              V2Badge(),
            ]),
            const SizedBox(height: 14),
            for (final n in _news)
              Container(
                margin: const EdgeInsets.only(bottom: 10),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(color: const Color(0x08FFFFFF), borderRadius: BorderRadius.circular(14), border: Border.all(color: Odin.stroke)),
                child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  SizedBox(width: 34, child: Text(n[0], style: const TextStyle(fontSize: 22))),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(n[1], style: const TextStyle(fontWeight: FontWeight.w700)),
                      const SizedBox(height: 4),
                      Text(n[2], style: const TextStyle(fontSize: 12.5, color: Odin.txtDim, height: 1.45)),
                    ]),
                  ),
                ]),
              ),
          ],
        ),
      ),
    );
