import 'dart:convert';
import 'package:http/http.dart' as http;

Stream<String> createSseTokens(String url, Map<String, String> headers, String? tokenQuery) async* {
  final req = http.Request('GET', Uri.parse(url));
  req.headers.addAll(headers);
  final client = http.Client();
  try {
    final resp = await client.send(req);
    String? event;
    await for (final line in resp.stream.transform(utf8.decoder).transform(const LineSplitter())) {
      if (line.startsWith('event:')) {
        event = line.substring(6).trim();
      } else if (line.startsWith('data:')) {
        final data = line.substring(5).trim();
        if (event == 'token') {
          try {
            yield (jsonDecode(data)['t'] ?? '').toString();
          } catch (_) {}
        } else if (event == 'done' || event == 'error') {
          break;
        }
      }
    }
  } finally {
    client.close();
  }
}
