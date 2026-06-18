import subprocess
import sys
import threading
from collections import deque
from pathlib import Path
from typing import Dict, Optional
from fastapi import FastAPI


app = FastAPI()

TEST_MODE = True

processes: Dict[str, subprocess.Popen] = {}
logs: Dict[str, deque] = {}


def make_key(controller_type, controller_id=None):
    if controller_id is None:
        return controller_type
    return f"{controller_type}_{controller_id}"


def build_command(controller_type: str, controller_id: Optional[int] = None):

    if controller_type == "system":
        return [PYTHON_BIN, "-u", "main.py"]

    if controller_id is None:
        return [PYTHON_BIN, "-u", "main.py", controller_type]

    return [PYTHON_BIN, "-u", "main.py", controller_type, str(controller_id)]


def read_process_output(key: str, process: subprocess.Popen):


    if key not in logs:
        logs[key] = deque(maxlen=1000)

    if process.stdout is None:
        return

    for line in iter(process.stdout.readline, ""):
        if not line:
            break

        line = line.rstrip()
        logs[key].append(line)

    process.stdout.close()


def start_controller(controller_type: str, controller_id: Optional[int] = None):
    key = process_key(controller_type, controller_id)

    existing = processes.get(key)

    if existing is not None and existing.poll() is None:
        return {
            "ok": True,
            "message": f"{key} already running",
            "pid": existing.pid,
        }

    command = build_command(controller_type, controller_id)

    logs[key] = deque(maxlen=1000)
    logs[key].append(f"[API] Starting {key}")
    logs[key].append(f"[API] Command: {' '.join(command)}")
    logs[key].append(f"[API] Working directory: {BASE_DIR}")

    process = subprocess.Popen(
        command,
        cwd=BASE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    processes[key] = process

    thread = threading.Thread(
        target=read_process_output,
        args=(key, process),
        daemon=True,
    )
    thread.start()

    return {
        "ok": True,
        "message": f"Started {key}",
        "pid": process.pid,
        "command": command,
    }


def stop_controller(controller_type: str, controller_id: Optional[int] = None):
    key = process_key(controller_type, controller_id)

    process = processes.get(key)

    if process is None:
        return {
            "ok": False,
            "message": f"{key} is not known by API",
        }

    if process.poll() is not None:
        return {
            "ok": True,
            "message": f"{key} already stopped",
            "returncode": process.returncode,
        }

    logs.setdefault(key, deque(maxlen=1000)).append(f"[API] Stopping {key}")

    process.terminate()

    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        logs[key].append(f"[API] Killing {key}")
        process.kill()
        process.wait(timeout=5)

    return {
        "ok": True,
        "message": f"Stopped {key}",
        "returncode": process.returncode,
    }


@app.get("/")
def root():
    return {
        "message": "ContRIS FastAPI controller is running"
    }


@app.get("/start/system")
def start_system():
    return start_controller("system")


@app.get("/stop/system")
def stop_system():
    return stop_controller("system")


@app.get("/start/generator")
def start_generator():
    return start_controller("generator")


@app.get("/stop/generator")
def stop_generator():
    return stop_controller("generator")


@app.get("/start/ris/{controller_id}")
def start_ris(controller_id: int):
    return start_controller("ris", controller_id)


@app.get("/stop/ris/{controller_id}")
def stop_ris(controller_id: int):
    return stop_controller("ris", controller_id)


@app.get("/start/rx/{controller_id}")
def start_rx(controller_id: int):
    return start_controller("rx", controller_id)


@app.get("/stop/rx/{controller_id}")
def stop_rx(controller_id: int):
    return stop_controller("rx", controller_id)


@app.post("/git/pull")
async def git_pull():
    """
    Wykonuje git pull w folderze projektu na hoście,
    na którym uruchomiony jest FastAPI.
    """

    try:
        result = subprocess.run(
            ["git", "pull"],
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            return {
                "success": True,
                "message": "Git pull completed successfully",
                "project_dir": str(PROJECT_DIR),
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        return {
            "success": False,
            "message": "Git pull failed",
            "project_dir": str(PROJECT_DIR),
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": "Git pull timeout exceeded",
            "project_dir": str(PROJECT_DIR),
            "stdout": "",
            "stderr": "The git pull command took too long and was interrupted.",
        }

    except Exception as error:
        return {
            "success": False,
            "message": "Git pull could not be executed",
            "project_dir": str(PROJECT_DIR),
            "stdout": "",
            "stderr": str(error),
        }


@app.post("/git/pull")
async def git_pull():
    """
    Wykonuje git pull w folderze projektu na hoście,
    na którym uruchomiony jest FastAPI.
    """

    try:
        result = subprocess.run(
            ["git", "pull"],
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            return {
                "success": True,
                "message": "Git pull completed successfully",
                "project_dir": str(PROJECT_DIR),
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        return {
            "success": False,
            "message": "Git pull failed",
            "project_dir": str(PROJECT_DIR),
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": "Git pull timeout exceeded",
            "project_dir": str(PROJECT_DIR),
            "stdout": "",
            "stderr": "The git pull command took too long and was interrupted.",
        }

    except Exception as error:
        return {
            "success": False,
            "message": "Git pull could not be executed",
            "project_dir": str(PROJECT_DIR),
            "stdout": "",
            "stderr": str(error),
        }


@app.get("/status")
def status():
    result = {}

    for key, process in processes.items():
        running = process.poll() is None

        result[key] = {
            "running": running,
            "pid": process.pid,
            "returncode": process.returncode,
        }

    return {
        "ok": True,
        "processes": result,
    }


@app.get("/logs")
def get_logs(controller: Optional[str] = None, lines: int = 100):


    if controller is not None:
        selected_logs = list(logs.get(controller, []))[-lines:]

        return {
            "ok": True,
            "controller": controller,
            "logs": selected_logs,
        }

    combined = []

    for key, log_buffer in logs.items():
        combined.append(f"== {key} ==")
        combined.extend(list(log_buffer)[-lines:])

    return {
        "ok": True,
        "controller": "all",
        "logs": combined[-lines:],
    }
