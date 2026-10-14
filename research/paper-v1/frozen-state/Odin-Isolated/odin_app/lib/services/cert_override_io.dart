import 'dart:io';

/// Mobile/desktop: trust the VM's self-signed certificate ONLY for our VM host (the reverse proxy on
/// 443). Every other host keeps normal, strict TLS validation. No domain/CA is required for the IP.
void installOdinCertOverride() {
  HttpOverrides.global = _OdinHttpOverrides();
}

const _trustedHosts = {'52.180.154.225', 'anchor.odinmarkets.com'};

class _OdinHttpOverrides extends HttpOverrides {
  @override
  HttpClient createHttpClient(SecurityContext? context) {
    final client = super.createHttpClient(context);
    client.badCertificateCallback = (X509Certificate cert, String host, int port) =>
        _trustedHosts.contains(host);
    return client;
  }
}
