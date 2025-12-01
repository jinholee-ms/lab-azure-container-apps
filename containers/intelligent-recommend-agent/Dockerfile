FROM python:3.12-slim

ENV PATH="/root/.local/bin:$PATH"

# RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates
# RUN curl -Ls https://astral.sh/uv/install.sh | sh

EXPOSE 8000

WORKDIR /intelligent-recommend-agent

COPY requirements.txt .
# RUN uv pip install --project .
RUN pip install -r requirements.txt

COPY . .

ENTRYPOINT ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]