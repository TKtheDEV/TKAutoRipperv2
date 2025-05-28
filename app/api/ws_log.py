from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
from app.core.job.manager import job_tracker

router = APIRouter()

@router.websocket("/ws/jobs/{job_id}")
async def job_ws(websocket: WebSocket, job_id: str):
    await websocket.accept()
    job = job_tracker.get(job_id)
    if not job or not job.runner:
        await websocket.close()
        return

    queue = asyncio.Queue()

    def handle_output(line: str):
        asyncio.create_task(queue.put({
            "type": "log",
            "line": line,
            "progress": job.progress,
            "status": job.status,
            "step": job.step_description
        }))

    job.runner.on_output = handle_output

    try:
        while True:
            msg = await queue.get()
            await websocket.send_json(msg)

    except WebSocketDisconnect:
        pass