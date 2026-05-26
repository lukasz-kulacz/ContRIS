import asyncio
from fastapi import FastAPI

app = FastAPI()

TEST_MODE = True

tasks = {}


def make_key(controller_type, controller_id=None):
    if controller_id is None:
        return controller_type
    return f"{controller_type}_{controller_id}"


async def long_task(controller_type, controller_id=None):
    key = make_key(controller_type, controller_id)

    if TEST_MODE:
        for i in range(3600):
            print(f"[TEST MODE] {key} working... {i + 1}/3600")
            await asyncio.sleep(1)

    else:
        command = build_command(controller_type, controller_id)
        print(f"[REAL MODE] Starting {key}: {' '.join(command)}")

        process = await asyncio.create_subprocess_exec(*command)
        await process.wait()

        print(f"[REAL MODE] {key} finished")


def build_command(controller_type, controller_id=None):
    if controller_type == "system":
        return ["python3", "main.py"]

    if controller_type == "generator":
        return ["python3", "main.py", "generator"]

    if controller_type == "rx":
        return ["python3", "main.py", "rx", str(controller_id)]

    if controller_type == "ris":
        return ["python3", "main.py", "ris", str(controller_id)]

    raise ValueError("Unknown controller type")


async def start_controller(controller_type, controller_id=None):
    key = make_key(controller_type, controller_id)

    if key in tasks and not tasks[key].done():
        return {"message": f"{key} is already running"}

    task = asyncio.create_task(long_task(controller_type, controller_id))
    tasks[key] = task

    return {
        "message": f"{key} started",
        "test_mode": TEST_MODE,
    }


async def stop_controller(controller_type, controller_id=None):
    key = make_key(controller_type, controller_id)

    if key not in tasks or tasks[key].done():
        return {"message": f"{key} is not running"}

    tasks[key].cancel()
    tasks.pop(key, None)

    return {"message": f"{key} stopped"}


@app.get("/start/system")
async def start_system():
    return await start_controller("system")


@app.get("/start/generator")
async def start_generator():
    return await start_controller("generator")


@app.get("/start/rx/{controller_id}")
async def start_rx(controller_id: int):
    return await start_controller("rx", controller_id)


@app.get("/start/ris/{controller_id}")
async def start_ris(controller_id: int):
    return await start_controller("ris", controller_id)


@app.get("/stop/system")
async def stop_system():
    return await stop_controller("system")


@app.get("/stop/generator")
async def stop_generator():
    return await stop_controller("generator")


@app.get("/stop/rx/{controller_id}")
async def stop_rx(controller_id: int):
    return await stop_controller("rx", controller_id)


@app.get("/stop/ris/{controller_id}")
async def stop_ris(controller_id: int):
    return await stop_controller("ris", controller_id)


@app.get("/status")
async def status():
    result = {}

    for key, task in tasks.items():
        result[key] = {
            "running": not task.done()
        }

    return {
        "test_mode": TEST_MODE,
        "controllers": result,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)