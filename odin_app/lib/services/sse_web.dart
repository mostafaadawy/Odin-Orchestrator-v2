import 'dart:async';
import 'dart:convert';
import 'dart:html' as html;

Stream<String> createSseTokens(String url, Map<String, String> headers, String? tokenQuery) {
  final controller = StreamController<String>();
  // EventSource can't set headers; the brain accepts the token as a query param for SSE.
  final full = (tokenQuery != null && tokenQuery.isNotEmpty)
      ? '$url${url.contains('?') ? '&' : '?'}token=${Uri.encodeComponent(tokenQuery)}'
      : url;
  final es = html.EventSource(full);
  es.addEventListener('token', (e) {
    try {
      final d = jsonDecode((e as html.MessageEvent).data as String);
      controller.add((d['t'] ?? '').toString());
    } catch (_) {}
  });
  void close(html.Event _) {
    es.close();
    if (!controller.isClosed) controller.close();
  }

  es.addEventListener('done', close);
  es.addEventListener('error', close);
  controller.onCancel = () => es.close();
  return controller.stream;
}
