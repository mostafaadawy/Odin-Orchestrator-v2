// Non-web stub — mobile/desktop. The monitor asset (mic + local /meeting endpoints) runs on the brain,
// reachable on web/desktop; on native mobile the button shows a hint instead (see whatsapp.dart).
bool get canOpenMonitor => false;
String registerMonitor(String pid) => '';
String brainBase() => 'http://localhost:18000';
void openReport(String url) {} // mobile: reports are embedded in chat + the bell SOC tab
