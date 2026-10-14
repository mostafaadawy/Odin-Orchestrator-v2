import 'sse_stub.dart' if (dart.library.html) 'sse_web.dart' if (dart.library.io) 'sse_io.dart';

/// Streams assistant tokens from an SSE endpoint (the brain's /scope/stream or /chat/stream).
/// Yields token strings; completes on the 'done'/'error' event. Platform impl is chosen by
/// conditional import (web = EventSource, io = http stream). Throws on unsupported platforms so
/// the caller can fall back to a non-streaming request.
Stream<String> sseTokens(String url, Map<String, String> headers, {String? tokenQuery}) =>
    createSseTokens(url, headers, tokenQuery);
