import asyncio
import contextlib
import json

from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.websockets import WebSocketDisconnect
import uvicorn

from agents import load_agents
from capabilities.mcp import init_module as init_mcp_module
from cmds.common import execute_interactive_shell
from common import console, init_ms_foundry_monitoring_module


app = FastAPI()


@app.websocket("/ws")
@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()

    input_queue: asyncio.Queue[str] = asyncio.Queue()

    async def sender():
        try:
            while True:
                chunk = await console.file.queue.get()
                await ws.send_json({"type": "stdout", "data": chunk})
        except WebSocketDisconnect:
            pass

    async def receiver():
        try:
            while True:
                raw = await ws.receive_text()

                # JSON이면 control/resize, 아니면 input으로 처리(하위호환)
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    await input_queue.put(raw)
                    continue

                if msg.get("type") == "resize":
                    cols = int(msg.get("cols") or 0)
                    if cols > 0:
                        console.width = cols   # ✅ Rich 폭을 프론트 cols에 맞춤
                    continue

                if msg.get("type") == "input":
                    await input_queue.put(msg.get("data", ""))
                    continue
        except WebSocketDisconnect:
            pass

    sender_task = asyncio.create_task(sender())
    receiver_task = asyncio.create_task(receiver())

    try:
        async def input_cb():
            await ws.send_json({"type": "prompt", "text": "😊 User > "})
            return await input_queue.get()   # ✅ 여기서만 입력을 받는다

        await execute_interactive_shell(input_cb=input_cb)
    except WebSocketDisconnect:
        print("WebSocket disconnected")
    finally:
        sender_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await sender_task


@app.get("/")
async def root():
    return FileResponse("static/index.html")


app.mount("/static", StaticFiles(directory="static"), name="static")


async def main():
    await init_ms_foundry_monitoring_module()
    await init_mcp_module()
    await load_agents()
    await uvicorn.Server(
        config=uvicorn.Config(app, host="0.0.0.0", port=8000),
    ).serve()