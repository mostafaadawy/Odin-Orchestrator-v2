// F-41 interim: the phone shows "enter this key on the desktop" for a key request and can never send a key.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:odin_app/screens/approvals.dart';

void main() {
  Future<List<List<dynamic>>> pump(WidgetTester t, Map<String, dynamic> item) async {
    final calls = <List<dynamic>>[];
    await t.pumpWidget(MaterialApp(home: Scaffold(body: ApprovalActions(
        item: item, onAct: (aid, ok) async { calls.add([aid, ok]); }))));
    return calls;
  }

  testWidgets('key request: desktop-only message, no field, no Approve', (t) async {
    final calls = await pump(t, {'id': 'k1', 'kind': 'key_request', 'key_name': 'KLAVIYO_KEY_X', 'desktop_only': true});
    expect(find.byKey(const ValueKey('desktop-only')), findsOneWidget);
    expect(find.textContaining('Enter this key on the desktop'), findsOneWidget);
    expect(find.byType(TextField), findsNothing);
    expect(find.byKey(const ValueKey('approve')), findsNothing);
    await t.tap(find.byKey(const ValueKey('reject')));
    expect(calls, [['k1', false]]);
  });

  testWidgets('normal proposal: Approve and Reject still shown', (t) async {
    final calls = await pump(t, {'id': 'p1', 'kind': 'change'});
    expect(find.byKey(const ValueKey('approve')), findsOneWidget);
    expect(find.byKey(const ValueKey('desktop-only')), findsNothing);
    await t.tap(find.byKey(const ValueKey('approve')));
    expect(calls, [['p1', true]]);
  });
}
