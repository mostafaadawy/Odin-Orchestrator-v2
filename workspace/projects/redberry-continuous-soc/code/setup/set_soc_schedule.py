import sys, pathlib, datetime
R = pathlib.Path("/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Orchestrator-v2")
sys.path.insert(0, str(R / "server"))
import scheduler  # type: ignore
PID = "redberry-continuous-soc"
PY = str(R / ".venv/bin/python"); SCRIPT = str(R / "server/soc_run.py")

tasks = scheduler.list_tasks(PID)
if not tasks:
    t = scheduler.create_task(PID, prompt="RedBerry Continuous SOC daily run",
                              schedule={"kind": "daily", "hhmm": "23:00", "tz": "America/New_York"},
                              title="🛡️ RedBerry SOC (daily 11PM ET)", kind_tag="soc-daily")
    tasks = [t]
tid = tasks[0]["id"]
scheduler.update_task(tid,
    run_cmd=f'"{PY}" "{SCRIPT}" --pid {{pid}} --mode full --cid {{cid}}',
    cwd=str(R),
    schedule={"kind": "daily", "hhmm": "23:00", "tz": "America/New_York"})
t = scheduler.get_task(tid)
print("task:", tid)
print("run_cmd:", t.get("run_cmd"))
print("schedule:", t.get("schedule"))
nr = t.get("nextRun")
if nr:
    from zoneinfo import ZoneInfo
    et = datetime.datetime.fromtimestamp(nr, ZoneInfo("America/New_York"))
    local = datetime.datetime.fromtimestamp(nr)
    print("nextRun (ET):", et.strftime("%Y-%m-%d %H:%M %Z"), "| (machine local):", local.strftime("%Y-%m-%d %H:%M"))
