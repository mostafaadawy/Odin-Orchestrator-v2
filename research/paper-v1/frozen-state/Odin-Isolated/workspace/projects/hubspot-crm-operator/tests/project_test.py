# Phase-7 project test — thin pointer to the SHARED test logic (workspace/shared/testing/phase7_lib.py).
# No duplication: the test body is shared; this file only supplies THIS project's id and calls it.
import sys, json, pathlib
PID = "hubspot-crm-operator"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "shared" / "testing"))
import phase7_lib

def main():
    r = phase7_lib.run_project_test(PID)
    print(json.dumps(r, indent=2))
    return r["passed"]

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
