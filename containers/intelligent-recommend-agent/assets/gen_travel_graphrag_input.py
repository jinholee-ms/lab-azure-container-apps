"""
build_travel_histories_for_graphrag.py

사전 준비:
  - 같은 디렉토리에 아래 CSV 3개가 있다고 가정
    - users.csv                (위에서 생성한 코드 그대로)
    - hotels.csv               (Google Maps 기반)
    - user_hotel_activity.csv  (이벤트 로그)

역할:
  - 각 user별로 여행 히스토리 요약 markdown 문서를 생성
  - GraphRAG 프로젝트의 input/ 디렉토리에 저장

이후:
  - graphrag 프로젝트 루트에서
      graphrag index --root .
    또는
      from graphrag import build_index
      build_index(config)
    실행
"""

from pathlib import Path

import pandas as pd


# =========================
# 경로 설정
# =========================

# 이 스크립트 파일 기준
BASE_DIR = Path(__file__).parent

# CSV들은 generator 스크립트와 같은 위치라고 가정
USERS_CSV = BASE_DIR / "users.csv"
HOTELS_CSV = BASE_DIR / "hotels.csv"
ACTIVITY_CSV = BASE_DIR / "user_hotel_activity.csv"

# 🔧 여기를 실제 GraphRAG 프로젝트의 input 폴더로 맞춰주면 됨
# 예: BASE_DIR / "graphrag_project" / "input"
GRAPHRAG_INPUT_DIR = BASE_DIR / "graphrag_input"
GRAPHRAG_INPUT_DIR.mkdir(parents=True, exist_ok=True)


# =========================
# 1) CSV 로드
# =========================

print("📥 Loading CSVs...")
users_df = pd.read_csv(USERS_CSV)
hotels_df = pd.read_csv(HOTELS_CSV)
activity_df = pd.read_csv(ACTIVITY_CSV)

required_user_cols = {"user_id", "name", "signup_date", "device_type"}
required_hotel_cols = {"hotel_id", "name", "city", "country", "rating"}
required_activity_cols = {
    "event_id",
    "user_id",
    "hotel_id",
    "event_type",
    "event_ts",
    "checkin_date",
    "checkout_date",
    "num_nights",
    "num_guests",
    "trip_purpose",
    "companions",
    "device_type",
    "source_channel",
    "price_per_night",
    "currency",
    "booking_id",
    "rating_score",
    "review_text",
}

missing_u = required_user_cols - set(users_df.columns)
missing_h = required_hotel_cols - set(hotels_df.columns)
missing_a = required_activity_cols - set(activity_df.columns)

if missing_u:
    raise ValueError(f"users.csv 에 다음 컬럼이 필요합니다: {missing_u}")
if missing_h:
    raise ValueError(f"hotels.csv 에 다음 컬럼이 필요합니다: {missing_h}")
if missing_a:
    raise ValueError(f"user_hotel_activity.csv 에 다음 컬럼이 필요합니다: {missing_a}")

users_df = users_df.set_index("user_id", drop=False)
hotels_df = hotels_df.set_index("hotel_id", drop=True)


# =========================
# 2) 한 사용자에 대한 여행 문서를 만드는 함수
# =========================

def build_user_profile_text(user_row: pd.Series,
                            user_activities: pd.DataFrame,
                            hotels_df: pd.DataFrame) -> str:
    """
    한 사용자의 전체 여행 히스토리를 Markdown으로 구성
    GraphRAG가 여기서 entity/relationship을 뽑아갈 것.
    """
    user_id = user_row["user_id"]
    name = user_row.get("name", f"user {user_id}")
    gender = user_row.get("gender", "")
    age = user_row.get("age", "")
    region = user_row.get("region_ko", "")
    device_type = user_row.get("device_type", "")
    signup_date = user_row.get("signup_date", "")

    # --------- 헤더 / 기본 정보 ----------
    lines = [
        f"# 사용자 여행 프로필: {name} (id={user_id})",
        "",
        "## 기본 정보",
        f"- 사용자 ID: `{user_id}`",
    ]
    if gender:
        lines.append(f"- 성별: {gender}")
    if age != "":
        lines.append(f"- 나이: {age}")
    if region:
        lines.append(f"- 주요 거주 지역: {region}")
    if device_type:
        lines.append(f"- 주 사용 기기: {device_type}")
    if signup_date != "":
        lines.append(f"- 가입일: {signup_date}")
    lines.append("")

    # --------- 전체 요약 섹션 ----------
    if user_activities.empty:
        lines.append("## 여행 활동 요약")
        lines.append("")
        lines.append("아직 기록된 호텔 검색/예약/리뷰 활동이 없습니다.")
        return "\n".join(lines) + "\n"

    lines.append("## 여행 활동 요약")
    lines.append("")

    total_events = len(user_activities)
    visited_hotels = user_activities["hotel_id"].nunique()
    cities = (
        user_activities.merge(
            hotels_df.reset_index()[["hotel_id", "city", "country"]],
            on="hotel_id",
            how="left",
        )[["city", "country"]]
        .dropna()
        .drop_duplicates()
    )

    lines.append(f"- 전체 이벤트 수: {total_events}건")
    lines.append(f"- 방문/검색한 호텔 수: {visited_hotels}곳")
    if not cities.empty:
        city_str = ", ".join(
            sorted(
                {f"{row.country} {row.city}" for _, row in cities.iterrows()}
            )
        )
        lines.append(f"- 방문/검색 지역: {city_str}")
    lines.append("")

    # 이벤트 타입별 통계
    lines.append("### 이벤트 타입별 분포")
    ev_counts = user_activities["event_type"].value_counts()
    for ev_type, cnt in ev_counts.items():
        lines.append(f"- {ev_type}: {cnt}건")
    lines.append("")

    # 평점 통계
    if user_activities["rating_score"].notna().any():
        rated = user_activities[user_activities["rating_score"].notna()]
        avg_rating = rated["rating_score"].mean()
        lines.append("### 평점 요약")
        lines.append(f"- 평점을 남긴 호텔 수: {len(rated)}건")
        lines.append(f"- 평균 평점: {avg_rating:.2f}/5")
        lines.append("")

    # --------- 상세 활동 로그 ----------
    lines.append("## 상세 활동 로그")
    lines.append("")

    # 최신 이벤트 순으로 정렬
    user_activities_sorted = user_activities.sort_values(
        by="event_ts", ascending=False
    )

    for _, act in user_activities_sorted.iterrows():
        event_id = act["event_id"]
        hotel_id = act["hotel_id"]
        event_type = act["event_type"]
        event_ts = act["event_ts"]
        checkin = act["checkin_date"]
        checkout = act["checkout_date"]
        num_nights = act["num_nights"]
        num_guests = act["num_guests"]
        trip_purpose = act["trip_purpose"]
        companions = act["companions"]
        device = act["device_type"]
        source_channel = act["source_channel"]
        price_per_night = act["price_per_night"]
        currency = act["currency"]
        booking_id = act["booking_id"]
        rating_score = act["rating_score"]
        review_text = act["review_text"]

        # 호텔 정보
        if hotel_id in hotels_df.index:
            h = hotels_df.loc[hotel_id]
            hotel_name = h.get("name", f"hotel {hotel_id}")
            city = h.get("city", "")
            country = h.get("country", "")
            hotel_rating = h.get("rating", "")
            user_ratings_total = h.get("user_ratings_total", "")
            price_level = h.get("price_level", "")
            address_short = h.get("address_short", "")
            types = h.get("types", "")
        else:
            hotel_name = f"hotel {hotel_id}"
            city = ""
            country = ""
            hotel_rating = ""
            user_ratings_total = ""
            price_level = ""
            address_short = ""
            types = ""

        lines.append(f"### 이벤트 ID: {event_id}")
        lines.append("")
        lines.append(f"- 이벤트 타입: **{event_type}**")
        lines.append(f"- 이벤트 시각: {event_ts}")
        lines.append(f"- 호텔: **{hotel_name}** (hotel_id={hotel_id})")

        loc_str = " / ".join([x for x in [country, city] if x])
        if loc_str:
            lines.append(f"- 호텔 위치: {loc_str}")
        if address_short:
            lines.append(f"- 호텔 주소(요약): {address_short}")
        if types:
            lines.append(f"- 호텔 타입: {types}")
        if hotel_rating not in ("", None):
            lines.append(f"- 호텔 평균 평점(전체): {hotel_rating} (리뷰 수={user_ratings_total})")
        if price_level not in ("", None):
            lines.append(f"- 호텔 가격 레벨(Google Price Level): {price_level}")

        lines.append(f"- 체크인 날짜: {checkin}")
        lines.append(f"- 체크아웃 날짜: {checkout}")
        lines.append(f"- 숙박 일수: {num_nights}박")
        lines.append(f"- 투숙 인원: {num_guests}명")
        lines.append(f"- 여행 목적: {trip_purpose}")
        lines.append(f"- 동행 유형: {companions}")
        lines.append(f"- 사용 기기: {device}")
        lines.append(f"- 검색/예약 채널: {source_channel}")
        lines.append(f"- 1박 당 가격: {price_per_night} {currency}")
        if booking_id:
            lines.append(f"- 예약 ID: {booking_id}")
        if pd.notna(rating_score):
            lines.append(f"- 사용자가 남긴 평점: {rating_score}/5")

        if isinstance(review_text, str) and review_text.strip():
            lines.append("")
            lines.append("#### 리뷰 내용")
            lines.append(review_text.strip())

        lines.append("")  # 이벤트 간 빈 줄

    return "\n".join(lines) + "\n"


# =========================
# 3) 사용자별로 md 파일 생성
# =========================

print("🧾 Building user travel history markdown files...")

# user별 activity groupby
activity_by_user = activity_df.groupby("user_id", dropna=False)

for user_id, user_row in users_df.iterrows():
    if user_id in activity_by_user.groups:
        user_acts = activity_by_user.get_group(user_id)
    else:
        # 활동이 없는 user도 빈 문서를 하나 만들어둠
        user_acts = activity_df.iloc[0:0].copy()

    doc_text = build_user_profile_text(user_row, user_acts, hotels_df)

    out_path = GRAPHRAG_INPUT_DIR / f"user_{user_id}.txt"
    out_path.write_text(doc_text, encoding="utf-8")
    print(f"  ✍️  {out_path.name} 생성")

print("\n✅ 모든 사용자 히스토리 문서 생성 완료!")
print(f"   GraphRAG input 디렉토리: {GRAPHRAG_INPUT_DIR}")
print("   이제 graphrag index / build_index() 를 실행하면 됩니다.")