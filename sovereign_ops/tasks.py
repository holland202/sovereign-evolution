#!/usr/bin/env python3
"""
SOVEREIGN OPS - tasks.py
========================
Minimal file-based task graph. No cloud, no workers, no orchestration engine.
One JSON file is the source of truth. This script is the only thing that
writes to it, so state stays consistent.

Rule adopted from meta_prompt.txt: a task is not "complete" until it has
attached evidence (a command that ran, a test that passed, a file that
exists). No self-reported completion.
"""
import json
import os
import sys
import subprocess
from datetime import datetime, timezone

STATE_FILE = os.path.join(os.path.dirname(__file__), "tasks.json")


def _load():
    if not os.path.exists(STATE_FILE):
        return {"goals": []}
    with open(STATE_FILE) as f:
        return json.load(f)


def _save(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def _now():
    return datetime.now(timezone.utc).isoformat()


def add_goal(goal_id, description):
    state = _load()
    state["goals"].append({
        "id": goal_id,
        "description": description,
        "created": _now(),
        "tasks": []
    })
    _save(state)
    print(f"Added goal '{goal_id}': {description}")


def add_task(goal_id, task_id, description, verify_cmd=None):
    """verify_cmd: a shell command whose exit code 0 = verified true.
    If None, task requires manual verification via verify_task()."""
    state = _load()
    for g in state["goals"]:
        if g["id"] == goal_id:
            g["tasks"].append({
                "id": task_id,
                "description": description,
                "status": "pending",       # pending -> in_progress -> verified | failed
                "verify_cmd": verify_cmd,
                "evidence": None,
                "created": _now(),
                "updated": _now(),
            })
            _save(state)
            print(f"Added task '{task_id}' to goal '{goal_id}'")
            return
    print(f"ERROR: goal '{goal_id}' not found", file=sys.stderr)
    sys.exit(1)


def start_task(goal_id, task_id):
    _set_status(goal_id, task_id, "in_progress")


def verify_task(goal_id, task_id, manual_evidence=None):
    """Run the task's verify_cmd if present, or accept manual evidence.
    This is the gate: nothing becomes 'verified' without evidence attached."""
    state = _load()
    for g in state["goals"]:
        if g["id"] != goal_id:
            continue
        for t in g["tasks"]:
            if t["id"] != task_id:
                continue
            if t["verify_cmd"]:
                result = subprocess.run(t["verify_cmd"], shell=True,
                                         capture_output=True, text=True)
                passed = result.returncode == 0
                t["evidence"] = {
                    "type": "command",
                    "cmd": t["verify_cmd"],
                    "returncode": result.returncode,
                    "stdout_tail": result.stdout[-500:],
                    "stderr_tail": result.stderr[-500:],
                    "timestamp": _now(),
                }
                t["status"] = "verified" if passed else "failed"
            elif manual_evidence:
                t["evidence"] = {"type": "manual", "note": manual_evidence, "timestamp": _now()}
                t["status"] = "verified"
            else:
                print("ERROR: no verify_cmd on task and no manual_evidence given. "
                      "Cannot mark verified without evidence.", file=sys.stderr)
                sys.exit(1)
            t["updated"] = _now()
            _save(state)
            print(f"Task '{task_id}': {t['status'].upper()}")
            if t["status"] == "failed":
                print(f"  stderr: {t['evidence']['stderr_tail']}")
            return
    print(f"ERROR: task '{task_id}' not found in goal '{goal_id}'", file=sys.stderr)
    sys.exit(1)


def _set_status(goal_id, task_id, status):
    state = _load()
    for g in state["goals"]:
        if g["id"] == goal_id:
            for t in g["tasks"]:
                if t["id"] == task_id:
                    t["status"] = status
                    t["updated"] = _now()
                    _save(state)
                    return
    print(f"ERROR: not found", file=sys.stderr)


def status():
    state = _load()
    for g in state["goals"]:
        total = len(g["tasks"])
        verified = sum(1 for t in g["tasks"] if t["status"] == "verified")
        failed = sum(1 for t in g["tasks"] if t["status"] == "failed")
        print(f"\n[{g['id']}] {g['description']}  ({verified}/{total} verified, {failed} failed)")
        for t in g["tasks"]:
            marker = {"pending": "  ", "in_progress": "> ", "verified": "OK", "failed": "XX"}[t["status"]]
            print(f"  {marker} {t['id']}: {t['description']}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        status()
    elif sys.argv[1] == "add-goal":
        add_goal(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "add-task":
        verify_cmd = sys.argv[5] if len(sys.argv) > 5 else None
        add_task(sys.argv[2], sys.argv[3], sys.argv[4], verify_cmd)
    elif sys.argv[1] == "start":
        start_task(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "verify":
        note = sys.argv[4] if len(sys.argv) > 4 else None
        verify_task(sys.argv[2], sys.argv[3], note)
    elif sys.argv[1] == "status":
        status()
    else:
        print("Usage: tasks.py [add-goal|add-task|start|verify|status] ...")
