#!/usr/bin/env python3
"""F-21 test (no LLM, no network): SOC IP enrichment uses a LOCAL GeoLite2 database; a visitor IP is never sent
to a third party. python f21_test.py <root> <iso>"""
import sys, os, pathlib, json, socket, types, tempfile
root = pathlib.Path(sys.argv[1]).resolve(); iso = pathlib.Path(sys.argv[2]).resolve()
os.chdir(root); sys.path.insert(0, str(root / "server")); sys.path.append(str(iso / "_research" / "testlibs"))
fails = []
def check(n, c, info=""):
    print(("PASS " if c else "FAIL ") + n + (f"  [{str(info)[:300]}]" if info and not c else ""))
    if not c: fails.append(n)
calls = []
_real = socket.socket.connect
def _no_net(self, addr): calls.append(addr); raise OSError("network blocked by test")
socket.socket.connect = _no_net
import socket as _s; _s.create_connection = lambda addr, *a, **k: (calls.append(addr), (_ for _ in ()).throw(OSError("blocked")))[1]
sys.modules["soc_intel_fusion"] = types.SimpleNamespace(fetch_bad_ips=lambda pid: {"map": {"203.0.113.9": "c2"}})
geo = pathlib.Path(tempfile.mkdtemp()) / "geoip"; geo.mkdir()
os.environ["ODIN_GEOIP_DIR"] = str(geo)
import soc_enrich as se
src = (root / "server" / "soc_enrich.py").read_text()
check("1: no third-party lookup left in the code (ip-api / http URL)", "http://ip-api.com/json" not in src and "urlopen" not in src)
e0 = se.enrich_ip("203.0.113.7", pid="f21-test")
check("2: without the database: says so, and makes NO network call", "not installed" in str(e0.get("state")) and not calls, (e0, calls))
from mmdb_writer import MMDBWriter
from netaddr import IPSet
w = MMDBWriter(4, "GeoLite2-City")
w.insert_network(IPSet(["203.0.113.0/24"]), {"country": {"names": {"en": "Egypt"}}, "city": {"names": {"en": "Cairo"}},
                                              "subdivisions": [{"names": {"en": "Cairo Governorate"}}]})
w.to_db_file(str(geo / "GeoLite2-City.mmdb"))
w = MMDBWriter(4, "GeoLite2-ASN")
w.insert_network(IPSet(["203.0.113.0/25"]), {"autonomous_system_number": 14061, "autonomous_system_organization": "DigitalOcean, LLC"})
w.insert_network(IPSet(["203.0.113.128/25"]), {"autonomous_system_number": 24835, "autonomous_system_organization": "Vodafone Data"})
w.to_db_file(str(geo / "GeoLite2-ASN.mmdb"))
getattr(se, "_READERS", {}).clear()
for f in pathlib.Path(se._cache("f21-test")).glob("*.json"): f.unlink()
e1 = se.enrich_ip("203.0.113.9", pid="f21-test"); e2 = se.enrich_ip("203.0.113.200", pid="f21-test")
check("3: with the local database: country/city/ASN filled", e1.get("state") == "ok" and e1.get("country") == "Egypt"
      and e1.get("city") == "Cairo" and "14061" in str(e1.get("asn")), e1)
check("4: hosting flag from the ASN name (DigitalOcean yes, Vodafone no); proxy/mobile left unknown",
      e1.get("hosting") is True and e2.get("hosting") is False and e1.get("proxy") is None, (e1, e2))
check("5: reputation cross-check still works (abuse.ch list)", e1.get("known_c2") is True)
n = se.narrative("203.0.113.9", {"hits": 8, "accounts": 8, "regularity": 0.95, "score": 0.85, "verdict": "bad"}, pid="f21-test")
check("6: the analyst narrative uses the local data", "DigitalOcean" in n and "Cairo" in n, n)
check("7: still NO network call after all lookups", not calls, calls)
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
