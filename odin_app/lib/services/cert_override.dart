// Conditional export: on mobile/desktop (dart:io) we install a cert override so the app trusts the
// VM's self-signed certificate for the reverse proxy (https://<VM_IP>/odin-anchor). On web there is no
// dart:io — the browser handles TLS — so we export a no-op stub.
export 'cert_override_stub.dart' if (dart.library.io) 'cert_override_io.dart';
