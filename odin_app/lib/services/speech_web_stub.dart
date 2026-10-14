// Non-web stub — mobile/desktop use flutter_tts instead (see voice.dart).
bool get ttsSupported => false;
void webSpeak(String text, {required bool arabic}) {}
void webStopSpeak() {}
String webTtsDiag() => 'native';
