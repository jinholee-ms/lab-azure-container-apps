from fastapi import FastAPI

from apis.housing import router as housing_router


app = FastAPI(
    title="Property Trend Agent",
    description="부동산 트렌드 분석 에이전트",
    version="0.0.1",
    contact={"name": "Jinho Lee", "email": "jinholee@microsoft.com"},
    openapi_url="/openapi.json",   # 기본값
    docs_url="/docs",
)

app.include_router(housing_router)