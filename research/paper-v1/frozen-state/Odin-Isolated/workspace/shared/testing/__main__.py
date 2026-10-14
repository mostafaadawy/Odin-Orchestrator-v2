"""Entry point so the whole suite runs by calling the folder:  python3 testing/  (or  python3 -m testing).
Delegates to run_all.py, which auto-discovers and runs every test (current and future)."""
import pathlib
import sys

print("Odin test suite — starting…", flush=True)   # immediate proof of life, before any heavy import
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import run_all  # noqa: E402

if __name__ == "__main__":
    sys.exit(run_all.main())
