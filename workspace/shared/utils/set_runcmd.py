import sys, pathlib
R = pathlib.Path("/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Orchestrator-v2")
sys.path.insert(0, str(R / "server"))
import scheduler
PID = "zoom-real-flow"
PY = str(R / ".venv/bin/python")
SCRIPT = str(R / "server/zoom_pipeline_run.py")
tasks = scheduler.list_tasks(PID)
if not tasks:
    t = scheduler.create_task(PID, prompt="Run the meeting pipeline",
                              schedule={"kind": "daily", "hhmm": "06:00"},
                              title="Zoom meeting pipeline", kind_tag="project-periodic")
    tasks = [t]
tid = tasks[0]["id"]
scheduler.update_task(tid,
    run_cmd=f'"{PY}" "{SCRIPT}" --pid {{pid}} --cid {{cid}}',
    cwd=str(R))
print("task", tid, "run_cmd ->", scheduler.get_task(tid).get("run_cmd"))
print("cwd  ->", scheduler.get_task(tid).get("cwd"))
