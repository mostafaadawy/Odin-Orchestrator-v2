import 'recpath_stub.dart' if (dart.library.io) 'recpath_io.dart';

/// A writable path for a new voice recording (mobile). On web, returns '' and the
/// recorder records to an in-memory blob whose URL is returned by stop().
Future<String> tempRecordPath() => createTempRecordPath();
