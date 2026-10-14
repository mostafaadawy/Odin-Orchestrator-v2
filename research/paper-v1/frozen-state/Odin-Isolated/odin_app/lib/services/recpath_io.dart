import 'dart:io';

Future<String> createTempRecordPath() async =>
    '${Directory.systemTemp.path}/odin_voice_${DateTime.now().millisecondsSinceEpoch}.m4a';
