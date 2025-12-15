FROM python:3.12-slim

ENV PATH="/root/.local/bin:$PATH"

# ─────────────────────────────────────────────────────────────
# Node.js (npm, npx) 설치 – MCP용 npx 실행에 필요
# ─────────────────────────────────────────────────────────────
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates gnupg && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*
RUN npm install -g @cablate/mcp-google-map

EXPOSE 8000

WORKDIR /intelligent-recommend-agent

COPY requirements.txt .
# RUN uv pip install --project .
RUN pip install -r requirements.txt

COPY . .

ENTRYPOINT ["python", "main.py", "web-terminal"]