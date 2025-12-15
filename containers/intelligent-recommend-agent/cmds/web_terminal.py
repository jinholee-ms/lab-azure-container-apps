import asyncio
import contextlib

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
async def ws_endpoint(ws: WebSocket):
    await ws.accept()

    async def sender():
        try:
            while True:
                chunk = await console.file.queue.get()
                await ws.send_text(chunk)
        except WebSocketDisconnect:
            pass

    sender_task = asyncio.create_task(sender())

    try:
        async def input_cb():
            return await ws.receive_text()

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