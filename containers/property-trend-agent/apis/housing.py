

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/trends", tags=["Trends"])

class PriceIn(BaseModel):
    city: str
    date: str

class PriceOut(BaseModel):
    city: str
    date: str
    average_price: float

@router.post(
    "/price",
    response_model=PriceOut,
    summary="도시별 평균 매매가 조회",
    description="특정 일자의 도시 평균 매매가를 반환합니다.",
    responses={
        200: {"description": "성공", "content": {"application/json": {"example": {
            "city":"Seoul", "date":"2025-09-01", "average_price": 985.3
        }}}},
        404: {"description": "데이터 없음"}
    },
)
async def get_price(payload: PriceIn) -> PriceOut:
    # ... 조회 로직
    return PriceOut(**payload.dict(), average_price=985.3)