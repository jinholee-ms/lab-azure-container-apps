from pathlib import Path
import random
import string
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# =========================
# 1. Parameters (scale)
# =========================
N_USERS = 100_000  # 유저 수
N_PRODUCTS = 50_000  # 상품 수
N_CAMPAIGNS = 500  # 캠페인 수
N_EVENTS = 5_000_000  # 이벤트 수 (여기서 대규모 조절)

random.seed(42)
np.random.seed(42)

# =========================
# 2. Util functions
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
# 3. users generation
# =========================

states = [
    "CA",
    "TX",
    "FL",
    "NY",
    "PA",
    "IL",
    "OH",
    "GA",
    "NC",
    "MI",
    "AZ",
    "NJ",
    "VA",
    "WA",
    "TN",
    "IN",
    "MO",
    "MD",
    "WI",
    "MN",
    "CO",
    "AL",
    "SC",
    "KY",
    "OR",
    "OK",
    "CT",
    "UT",
    "IA",
    "NV",
]

device_types = ["mobile", "desktop", "tablet", "tv", "wearable"]
membership_levels = ["free", "bronze", "silver", "gold", "vip"]
categories = [
    "gaming",
    "shopping",
    "travel",
    "video",
    "music",
    "books",
    "education",
    "finance",
]

signup_start = datetime(2020, 1, 1)
signup_end = datetime(2025, 11, 1)

user_ids = np.arange(1, N_USERS + 1)

from faker import Faker

fake = Faker("en_US")  # 미국식 이름/주소 생성

users = pd.DataFrame(
    {
        "user_id": user_ids,
        "name": [fake.name() for _ in range(N_USERS)],  # 랜덤 미국식 이름
        "address": [fake.address() for _ in range(N_USERS)],  # 랜덤 미국식 주소
        "phone_number": [
            fake.phone_number() for _ in range(N_USERS)
        ],  # 랜덤 미국식 전화번호
        "email": [fake.email() for _ in range(N_USERS)],  # 랜덤 이메일
        "signup_date": [
            random_date(signup_start, signup_end).date() for _ in range(N_USERS)
        ],
        "gender": np.random.choice(["M", "F", "U"], size=N_USERS, p=[0.48, 0.48, 0.04]),
        "age": np.random.randint(18, 70, size=N_USERS),
        "state": np.random.choice(states, size=N_USERS),
        "device_type": np.random.choice(
            device_types, size=N_USERS, p=[0.6, 0.20, 0.1, 0.075, 0.025]
        ),
        "membership_level": np.random.choice(membership_levels, size=N_USERS),
        "preferred_category": np.random.choice(categories, size=N_USERS),
    }
)

print("users generated:", users.shape)

# =========================
# 4. products generation
# =========================

category_mid_map = {
    "gaming": [
        "RPG",
        "casual",
        "shooter",
        "puzzle",
        "sports",
        "strategy",
        "adventure",
        "racing",
        "simulation",
    ],
    "shopping": [
        "fashion",
        "electronics",
        "food",
        "home",
        "beauty",
        "baby",
        "sports_goods",
        "furniture",
        "hobby",
        "pet",
        "automotive",
        "health",
    ],
    "travel": [
        "flight",
        "hotel",
        "rental_car",
        "tour",
        "cruise",
        "activity",
        "camping",
        "domestic",
        "overseas",
        "resort",
        "city",
        "backpacking",
    ],
    "video": [
        "movie",
        "drama",
        "variety",
        "animation",
        "documentary",
        "webtoon",
        "music_video",
        "sports_streaming",
        "news",
        "education",
    ],
    "music": [
        "kpop",
        "ballad",
        "hiphop",
        "jazz",
        "classical",
        "rock",
        "pop",
        "edm",
        "ost",
        "indie",
        "trot",
    ],
    "books": [
        "novel",
        "essay",
        "business",
        "it",
        "self_help",
        "humanities",
        "science",
        "art",
        "children",
        "comic",
    ],
    "education": [
        "language",
        "coding",
        "certificate",
        "hobby",
        "early_education",
        "university_course",
        "job_training",
        "online_course",
        "study_group",
        "mentoring",
    ],
    "finance": [
        "card",
        "insurance",
        "loan",
        "investment",
        "pension",
        "fx",
        "real_estate",
        "asset_management",
        "tax",
        "accounting",
    ],
}

publisher_names = [
    "Alpha Games",
    "Beta Entertainment",
    "Korea Shopping",
    "Hangang Travel",
    "Studio Seoul",
    "Music Factory",
    "Hana Books",
    "Future Education Lab",
    "Korea Finance",
    "Digital World",
    "Global Media",
    "Smart Learning",
    "Trend Capital",
    "NextGen",
    "EduTech",
    "Premium Contents",
    "All That Music",
    "Book & Story",
    "Travel Planner",
    "Digital Life",
]

product_ids = np.arange(1, N_PRODUCTS + 1)
product_large = np.random.choice(categories, size=N_PRODUCTS)

product_mid = [np.random.choice(category_mid_map[cat]) for cat in product_large]


def make_product_name(cat_large, cat_mid, idx):
    base = {
        "gaming": "Legend",
        "shopping": "Special Deal",
        "travel": "Package",
        "video": "Premium",
        "music": "Best",
        "books": "Smart",
        "education": "Online Course",
        "finance": "Plus",
    }.get(cat_large, "Special")
    return f"{base} {cat_mid} {idx}"


release_start = datetime(2018, 1, 1)
release_end = datetime(2025, 11, 1)

products = pd.DataFrame(
    {
        "product_id": product_ids,
        "product_name": [
            make_product_name(cat_l, cat_m, i)
            for i, (cat_l, cat_m) in enumerate(zip(product_large, product_mid), start=1)
        ],
        "category_large": product_large,
        "category_mid": product_mid,
        "price": np.round(
            np.random.lognormal(mean=3.5, sigma=0.6, size=N_PRODUCTS) * 10, 0
        ),
        "publisher_name": np.random.choice(publisher_names, size=N_PRODUCTS),
        "release_date": [
            random_date(release_start, release_end).date() for _ in range(N_PRODUCTS)
        ],
        "is_active": np.random.choice([True, False], size=N_PRODUCTS, p=[0.85, 0.15]),
        "tags": [
            ",".join(
                np.random.choice(
                    [
                        "popular",
                        "new",
                        "discount",
                        "event",
                        "limited",
                        "recommended",
                        "premium",
                    ],
                    size=np.random.randint(1, 4),
                    replace=False,
                )
            )
            for _ in range(N_PRODUCTS)
        ],
    }
)

print("products generated:", products.shape)

# =========================
# 5. campaigns generation
# =========================

objectives = ["install", "reengage", "purchase", "awareness"]
campaign_ids = np.arange(1, N_CAMPAIGNS + 1)


def make_campaign_name(idx):
    return f"Campaign {idx} - {np.random.choice(['new users', 'returning users', 'repeat purchase'])}"


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
            "campaign_name": make_campaign_name(cid),
            "objective": random.choice(objectives),
            "start_date": start.date(),
            "end_date": end.date(),
            "target_gender": random.choice(["M", "F", "ALL"]),
            "target_age_min": age_min,
            "target_age_max": age_max,
            "target_state": random.choice(
                ["all", "West", "Midwest", "South", "Northeast"] + states
            ),
            "target_category": random.choice(categories),
            "budget": float(np.round(np.random.uniform(5_000_000, 200_000_000), -4)),
        }
    )

campaigns = pd.DataFrame(campaigns_data)
print("campaigns generated:", campaigns.shape)

# =========================
# 6. events generation (large scale)
# =========================

event_types = ["impression", "click", "install", "open", "purchase", "like"]
platforms = ["android", "ios", "web"]
traffic_sources = ["organic", "push", "search", "ad", "banner"]

event_start = datetime(2023, 1, 1)
event_end = datetime(2025, 11, 1)

# user, product, campaign sampling
user_sample = np.random.choice(user_ids, size=N_EVENTS)
product_sample = np.random.choice(product_ids, size=N_EVENTS)

# 일부만 캠페인 매핑 (예: 40% 정도)
campaign_sample = np.random.choice(
    np.append(campaign_ids, [np.nan] * int(N_CAMPAIGNS * 1.5)), size=N_EVENTS
)

# 이벤트 타입 비율
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

print("events generated:", events.shape)

# =========================
# 7. Save to CSV
# =========================
assets_path = Path() / "assets"
assets_path.mkdir(parents=True, exist_ok=True)

users.to_csv(assets_path / "users-us.csv", index=False)
products.to_csv(assets_path / "products-us.csv", index=False)
campaigns.to_csv(assets_path / "campaigns-us.csv", index=False)
events.to_csv(assets_path / "events-us.csv", index=False)

print("CSV files saved:")
print("  users-us.csv")
print("  products-us.csv")
print("  campaigns-us.csv")
print("  events-us.csv")
