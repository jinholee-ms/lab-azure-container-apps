import random
import string
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# =========================
# 1. 파라미터 (규모 조절)
# =========================
N_USERS = 100_000  # 유저 수
N_PRODUCTS = 50_000  # 상품 수
N_CAMPAIGNS = 500  # 캠페인 수
N_EVENTS = 5_000_000  # 이벤트 수 (여기서 대규모 조절)

random.seed(42)
np.random.seed(42)

# =========================
# 2. 유틸 함수
# =========================


def random_date(start: datetime, end: datetime) -> datetime:
    """start~end 사이 랜덤 날짜"""
    delta = end - start
    rand_days = random.randrange(delta.days + 1)
    rand_seconds = random.randrange(24 * 3600)
    return start + timedelta(days=rand_days, seconds=rand_seconds)


def random_session_id():
    return "".join(random.choices(string.ascii_letters + string.digits, k=32))


# =========================
# 3. users 생성
# =========================

regions_ko = [
    "서울",
    "경기",
    "인천",
    "부산",
    "대구",
    "광주",
    "대전",
    "울산",
    "강원",
    "충북",
    "충남",
    "전북",
    "전남",
    "경북",
    "경남",
    "제주",
]
device_types = ["mobile", "pc", "tablet", "tv", "wearable"]
membership_levels = ["free", "bronze", "silver", "gold", "vip"]
categories_ko = ["게임", "쇼핑", "여행", "영상", "음악", "도서", "교육", "금융"]

signup_start = datetime(2020, 1, 1)
signup_end = datetime(2025, 11, 1)

user_ids = np.arange(1, N_USERS + 1)

from faker import Faker

fake = Faker("ko_KR")  # 한국식 이름/주소 생성

users = pd.DataFrame(
    {
        "user_id": user_ids,
        "name": [fake.name() for _ in range(N_USERS)],  # 랜덤 한국식 이름
        "address": [fake.address() for _ in range(N_USERS)],  # 랜덤 한국식 주소
        "phone_number": [
            fake.phone_number() for _ in range(N_USERS)
        ],  # 랜덤 한국식 전화번호
        "email": [fake.email() for _ in range(N_USERS)],  # 랜덤 이메일
        "signup_date": [
            random_date(signup_start, signup_end).date() for _ in range(N_USERS)
        ],
        "gender": np.random.choice(["M", "F", "U"], size=N_USERS, p=[0.48, 0.48, 0.04]),
        "age": np.random.randint(15, 65, size=N_USERS),
        "region_ko": np.random.choice(regions_ko, size=N_USERS),
        "device_type": np.random.choice(
            device_types, size=N_USERS, p=[0.6, 0.20, 0.1, 0.075, 0.025]
        )
    }
)

print("users 생성 완료:", users.shape)

# =========================
# 4. products 생성
# =========================

category_mid_map = {
    "게임": [
        "RPG",
        "캐주얼",
        "슈팅",
        "퍼즐",
        "스포츠",
        "전략",
        "어드벤처",
        "레이싱",
        "시뮬레이션",
    ],
    "쇼핑": [
        "패션",
        "전자제품",
        "식품",
        "생활용품",
        "뷰티",
        "유아동",
        "스포츠용품",
        "가구",
        "취미",
        "반려동물",
        "자동차",
        "건강",
    ],
    "여행": [
        "항공",
        "호텔",
        "렌터카",
        "투어",
        "크루즈",
        "액티비티",
        "캠핑",
        "국내",
        "해외",
        "휴양지",
        "도시",
        "배낭",
    ],
    "영상": [
        "영화",
        "드라마",
        "예능",
        "애니메이션",
        "다큐멘터리",
        "웹툰",
        "뮤직비디오",
        "스포츠중계",
        "뉴스",
        "교육",
    ],
    "음악": [
        "K-POP",
        "발라드",
        "힙합",
        "재즈",
        "클래식",
        "록",
        "팝",
        "EDM",
        "OST",
        "인디",
        "트로트",
    ],
    "도서": [
        "소설",
        "에세이",
        "경제경영",
        "IT",
        "자기계발",
        "인문",
        "과학",
        "예술",
        "어린이",
        "만화",
    ],
    "교육": [
        "어학",
        "코딩",
        "자격증",
        "취미",
        "유아교육",
        "대학강의",
        "직무교육",
        "온라인강의",
        "스터디",
        "멘토링",
    ],
    "금융": [
        "카드",
        "보험",
        "대출",
        "투자",
        "연금",
        "외환",
        "부동산",
        "재테크",
        "세금",
        "회계",
    ],
}

publisher_names = [
    "알파게임즈",
    "베타엔터테인먼트",
    "코리아쇼핑",
    "한강트래블",
    "스튜디오서울",
    "뮤직팩토리",
    "하나북스",
    "미래교육연구소",
    "코리아파이낸스",
    "디지털월드",
    "글로벌미디어",
    "스마트러닝",
    "트렌드캐피털",
    "넥스트젠",
    "에듀테크",
    "프리미엄콘텐츠",
    "올댓뮤직",
    "북앤스토리",
    "여행플래너",
    "디지털라이프",
]

product_ids = np.arange(1, N_PRODUCTS + 1)
product_large = np.random.choice(categories_ko, size=N_PRODUCTS)

product_mid = [np.random.choice(category_mid_map[cat]) for cat in product_large]


def make_product_name(cat_large, cat_mid, idx):
    base = {
        "게임": "레전드",
        "쇼핑": "스페셜딜",
        "여행": "패키지",
        "영상": "프리미엄",
        "음악": "베스트",
        "도서": "스마트",
        "교육": "인강",
        "금융": "플러스",
    }.get(cat_large, "스페셜")
    return f"{base} {cat_mid} {idx}"


release_start = datetime(2018, 1, 1)
release_end = datetime(2025, 11, 1)

products = pd.DataFrame(
    {
        "product_id": product_ids,
        "product_name_ko": [
            make_product_name(cat_l, cat_m, i)
            for i, (cat_l, cat_m) in enumerate(zip(product_large, product_mid), start=1)
        ],
        "category_large_ko": product_large,
        "category_mid_ko": product_mid,
        "price": np.round(
            np.random.lognormal(mean=3.5, sigma=0.6, size=N_PRODUCTS) * 10, 0
        ),
        "publisher_name_ko": np.random.choice(publisher_names, size=N_PRODUCTS),
        "release_date": [
            random_date(release_start, release_end).date() for _ in range(N_PRODUCTS)
        ],
        "is_active": np.random.choice([True, False], size=N_PRODUCTS, p=[0.85, 0.15]),
        "tags_ko": [
            ",".join(
                np.random.choice(
                    ["인기", "신규", "할인", "이벤트", "한정판", "추천", "프리미엄"],
                    size=np.random.randint(1, 4),
                    replace=False,
                )
            )
            for _ in range(N_PRODUCTS)
        ],
    }
)

print("products 생성 완료:", products.shape)

# =========================
# 5. campaigns 생성
# =========================

objectives = ["install", "reengage", "purchase", "awareness"]
campaign_ids = np.arange(1, N_CAMPAIGNS + 1)


def make_campaign_name(idx):
    return f"{idx}차 {np.random.choice(['신규', '복귀', '재구매'])} 유저 타겟 캠페인"


campaign_start_base = datetime(2022, 1, 1)
campaign_end_base = datetime(2025, 12, 31)

campaigns_data = []
for cid in campaign_ids:
    start = random_date(campaign_start_base, campaign_end_base - timedelta(days=30))
    end = start + timedelta(days=random.randint(7, 90))
    if end > campaign_end_base:
        end = campaign_end_base
    age_min = random.choice([10, 20, 30, 40])
    age_max = age_min + random.choice([9, 14, 19])
    campaigns_data.append(
        {
            "campaign_id": cid,
            "campaign_name_ko": make_campaign_name(cid),
            "objective": random.choice(objectives),
            "start_date": start.date(),
            "end_date": end.date(),
            "target_gender": random.choice(["M", "F", "ALL"]),
            "target_age_min": age_min,
            "target_age_max": age_max,
            "target_region_ko": random.choice(
                ["전체", "서울", "수도권", "영남", "호남", "충청"]
            ),
            "target_category_ko": random.choice(categories_ko),
            "budget": float(np.round(np.random.uniform(5_000_000, 200_000_000), -4)),
        }
    )

campaigns = pd.DataFrame(campaigns_data)
print("campaigns 생성 완료:", campaigns.shape)

# =========================
# 6. events 생성 (대규모)
# =========================

event_types = ["impression", "click", "install", "open", "purchase", "like"]
platforms = ["android", "ios", "web"]
traffic_sources = ["organic", "push", "search", "ad", "banner"]

event_start = datetime(2023, 1, 1)
event_end = datetime(2025, 11, 1)

# user, product, campaign를 랜덤 샘플링
user_sample = np.random.choice(user_ids, size=N_EVENTS)
product_sample = np.random.choice(product_ids, size=N_EVENTS)

# 캠페인은 일부만 매핑 (예: 40% 정도)
campaign_sample = np.random.choice(
    np.append(campaign_ids, [np.nan] * int(N_CAMPAIGNS * 1.5)), size=N_EVENTS
)

# 이벤트 타입 비율 (임의 설정)
event_type_sample = np.random.choice(
    event_types,
    size=N_EVENTS,
    p=[0.55, 0.20, 0.03, 0.10, 0.05, 0.07],  # impression이 가장 많게
)

event_ts_sample = [random_date(event_start, event_end) for _ in range(N_EVENTS)]

platform_sample = np.random.choice(platforms, size=N_EVENTS, p=[0.6, 0.3, 0.1])
traffic_sample = np.random.choice(
    traffic_sources, size=N_EVENTS, p=[0.5, 0.1, 0.15, 0.2, 0.05]
)

position_sample = np.random.randint(1, 21, size=N_EVENTS)  # 전시 순위 1~20
session_ids = [random_session_id() for _ in range(N_EVENTS)]

# price / quantity / revenue / is_conversion 생성
price_map = products.set_index("product_id")["price"].to_dict()

prices = []
quantities = []
revenues = []
is_conversions = []

for i in range(N_EVENTS):
    et = event_type_sample[i]
    pid = product_sample[i]
    base_price = price_map.get(pid, 0.0)

    if et == "purchase":
        q = np.random.randint(1, 4)
        p = float(base_price)
        r = float(p * q)
        conv = True
    elif et in ["install", "open"]:
        # 설치/오픈은 매출 0, 전환 True
        q = None
        p = 0.0
        r = 0.0
        conv = True
    else:
        q = None
        p = 0.0
        r = 0.0
        conv = False

    prices.append(p)
    quantities.append(q)
    revenues.append(r)
    is_conversions.append(conv)

events = pd.DataFrame(
    {
        "event_id": np.arange(1, N_EVENTS + 1),
        "event_ts": event_ts_sample,
        "user_id": user_sample,
        "product_id": product_sample,
        "event_type": event_type_sample,
        "campaign_id": campaign_sample,
        "platform": platform_sample,
        "traffic_source": traffic_sample,
        "position": position_sample,
        "session_id": session_ids,
        "price": prices,
        "quantity": quantities,
        "is_conversion": is_conversions,
        "revenue": revenues,
    }
)

print("events 생성 완료:", events.shape)

# =========================
# 7. CSV 저장
# =========================

users.to_csv("users-kr.csv", index=False)
products.to_csv("products-kr.csv", index=False)
campaigns.to_csv("campaigns-kr.csv", index=False)
events.to_csv("events-kr.csv", index=False)

print("CSV 파일 저장 완료:")
print("  users-kr.csv")
print("  products-kr.csv")
print("  campaigns-kr.csv")
print("  events-kr.csv")
