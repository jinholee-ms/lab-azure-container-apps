from fastapi import FastAPI

from apis.housing import router as housing_router


app = FastAPI(
    title="Property Trend Agent",
    description="부동산 트렌드 분석 에이전트",
    version="1.0.0",
    contact={"name": "Jinho Lee", "email": "jinholee@example.com"},
    openapi_url="/openapi.json",   # 기본값
    docs_url="/docs",              # Swagger UI
    redoc_url="/redoc",            # ReDoc
)

app.include_router(housing_router)