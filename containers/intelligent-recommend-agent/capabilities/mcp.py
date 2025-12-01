import atexit
from datetime import timedelta
import httpx
import subprocess
import time

from langchain_mcp_adapters.client import MultiServerMCPClient

from common import settings, console


mcp_client: MultiServerMCPClient = None
_mcp_processes: dict[str, subprocess.Popen] = {}
_mcp_cmds: list[dict] = {
    "mcp-google-map": {
        "port": settings.GOOGLE_MAP_MCP_PORT,
        "cmd": [
            "npx",
            "--yes",
            "@cablate/mcp-google-map",
            "--port",
            str(settings.GOOGLE_MAP_MCP_PORT),
            "--apikey",
            settings.GOOGLE_MAP_MCP_API_KEY,
        ],
    },
}


def start_mcp_servers(wait_timeout: int = 10) -> None:
    for name, props in _mcp_cmds.items():
        process = subprocess.Popen(
            props["cmd"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        console.print(f"🔺 Started MCP server '{name}' with PID {process.pid}.")

        # Wait for the server to be ready
        ready = False
        last_exception = None
        start = time.time()
        while time.time() - start < wait_timeout:
            try:
                if r := httpx.get(f"http://127.0.0.1:{props['port']}/mcp", timeout=1):
                    if r.status_code == 200:
                        ready = True
                        break
                    elif r.status_code == 400:
                        console.print(
                            f"⚠️ MCP server '{name}' responded with 400 Bad Request, assuming it's ready."
                        )
                        ready = True
                        break
            except Exception as e:
                console.print(f"⚠️ Exception checking MCP server '{name}'...")
                last_exception = e
            time.sleep(0.5)

        if not ready:
            console.print("⛔ MCP server did not start in time.")
            if last_exception:
                console.print(f"Last exception: {last_exception}")
        else:
            console.print(f"✅ MCP server '{name}' is ready.")
            _mcp_processes[name] = process

    atexit.register(cleanup_mcp_servers)


def cleanup_mcp_servers() -> None:
    for name, process in _mcp_processes.items():
        if process.poll() is None:
            process.terminate()  # or process.kill()
            console.print(f"🔻 Subprocess '{name}' terminated.")


async def init_module() -> None:
    start_mcp_servers()

    global mcp_client
    mcp_client = MultiServerMCPClient(
        {
            "naver-web": {
                "transport": "stdio",
                "command": "npx",
                "args": ["-y", "@isnow890/naver-search-mcp"],
                "env": {
                    "NAVER_CLIENT_ID": settings.NAVER_DEV_CLIENT_ID,
                    "NAVER_CLIENT_SECRET": settings.NAVER_DEV_CLIENT_SECRET,
                },
            },
            "google-places": {
                "transport": "streamable_http",
                "url": f"http://localhost:{settings.GOOGLE_MAP_MCP_PORT}/mcp",
                # "timeout": timedelta(seconds=30),          # 전체 요청 타임아웃
                # "sse_read_timeout": timedelta(seconds=60), # 스트림 읽기 타임아웃
                # "headers": {
                #     "X-Google-Maps-API-Key": settings.GOOGLE_MAP_MCP_API_KEY,
                # }
            },
            "openweathermap": {
                "transport": "stdio",
                "command": "npx",
                "args": ["-y", "mcp-openweathermap"],
                "env": {
                    "OPENWEATHER_API_KEY": settings.OPENWEATHER_API_KEY,
                },
                "capabilities": {
                    "completion": False,
                },
            },
        }
    )


def get_mcp_client() -> MultiServerMCPClient:
    return mcp_client
