import os
import time
import random
from datetime import datetime, timedelta
from typing import List, Dict

import numpy as np
import pandas as pd
from faker import Faker
from dotenv import load_dotenv
import googlemaps


# ============================================================
# 공통 설정
# ============================================================

N_USERS = 50              # 생성할 사용자 수
N_HOTELS_PER_CITY = 30    # 도시별 최대 호텔 수
N_ACTIVITIES = 200        # user-hotel activity 이벤트 수

TARGET_CITIES = [
    # name, center_lat, center_lng, search_radius_meters
    ("Paris", 48.8566, 2.3522, 6000),
    ("Seoul", 37.5665, 126.9780, 6000),
    ("Nairobi", -1.2921, 36.8219, 6000),
]


# ============================================================
# 유틸리티 함수
# ============================================================

def random_date(start: datetime, end: datetime) -> datetime:
    delta = end - start
    return start + timedelta(days=random.randint(0, delta.days))


def init_google_maps_client() -> googlemaps.Client:
    load_dotenv()
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_MAPS_API_KEY 환경변수를 설정하거나 .env 에 넣어주세요.")
    return googlemaps.Client(key=api_key)


# ============================================================
# 1) 사용자(users.csv) 생성
# ============================================================

def generate_users(n_users: int = N_USERS) -> pd.DataFrame:
    fake = Faker("ko_KR")

    signup_start = datetime(2022, 1, 1)
    signup_end = datetime(2024, 12, 31)

    regions_ko = ["서울", "경기", "부산", "대구", "제주", "인천", "광주", "대전"]
    device_types = ["iOS", "Android", "Web", "Tablet", "Other"]

    user_ids = [f"user_{i:04d}" for i in range(1, n_users + 1)]

    users = pd.DataFrame(
        {
            "user_id": user_ids,
            "name": [fake.name() for _ in range(n_users)],
            "address": [fake.address().replace("\n", " ") for _ in range(n_users)],
            "phone_number": [fake.phone_number() for _ in range(n_users)],
            "email": [fake.email() for _ in range(n_users)],
            "signup_date": [
                random_date(signup_start, signup_end).date() for _ in range(n_users)
            ],
            "gender": np.random.choice(["M", "F", "U"], size=n_users,
                                       p=[0.48, 0.48, 0.04]),
            "age": np.random.randint(15, 65, size=n_users),
            "region_ko": np.random.choice(regions_ko, size=n_users),
            "device_type": np.random.choice(
                device_types, size=n_users, p=[0.6, 0.20, 0.1, 0.075, 0.025]
            ),
        }
    )

    return users


# ============================================================
# 2) Google Maps 기반 hotel 목록(hotels_from_google_maps.csv) 생성
# ============================================================

def search_hotels_in_city(
    gmaps_client: googlemaps.Client,
    city_name: str,
    lat: float,
    lng: float,
    radius: int = 5000,
    max_results: int = 30,
) -> List[Dict]:
    """
    Google Places 'nearby_search' 를 사용해서 특정 도시 주변 호텔 검색
    type='lodging' 으로 숙소/호텔 전체 검색
    """
    all_results: List[Dict] = []
    page_token = None

    while True:
        params = {
            "location": (lat, lng),
            "radius": radius,
            "type": "lodging",
        }
        if page_token:
            params["page_token"] = page_token

        resp = gmaps_client.places_nearby(**params)
        results = resp.get("results", [])
        all_results.extend(results)

        page_token = resp.get("next_page_token")
        if not page_token:
            break
        if len(all_results) >= max_results:
            break

        # next_page_token 활성화까지 딜레이 필요 (공식 가이드)
        time.sleep(2)

    return all_results[:max_results]


def collect_hotels_from_google_maps(
    gmaps_client: googlemaps.Client,
    target_cities=TARGET_CITIES,
    max_per_city=N_HOTELS_PER_CITY,
) -> pd.DataFrame:
    rows = []
    hotel_id_counter = 1

    for city_name, lat, lng, radius in target_cities:
        print(f"🔍 Searching hotels in {city_name}...")
        places = search_hotels_in_city(
            gmaps_client, city_name, lat, lng, radius=radius, max_results=max_per_city
        )

        for p in places:
            place_id = p.get("place_id")
            name = p.get("name")
            loc = p.get("geometry", {}).get("location", {})
            rating = p.get("rating")
            user_ratings_total = p.get("user_ratings_total")
            price_level = p.get("price_level")  # 0~4 or None
            vicinity = p.get("vicinity")  # 간단 주소/지명
            types = ",".join(p.get("types", []))

            row = {
                "hotel_id": f"hotel_{hotel_id_counter:05d}",
                "google_place_id": place_id,
                "name": name,
                "city": city_name,
                "country": None,
                "latitude": loc.get("lat"),
                "longitude": loc.get("lng"),
                "rating": rating,
                "user_ratings_total": user_ratings_total,
                "price_level": price_level,
                "address_short": vicinity,
                "types": types,
            }
            rows.append(row)
            hotel_id_counter += 1

    df = pd.DataFrame(rows)

    # city → country 간단 매핑
    df["country"] = df["city"].map(
        {
            "Paris": "France",
            "Seoul": "South Korea",
            "Nairobi": "Kenya",
        }
    )

    return df


# ============================================================
# 3) user–hotel activity(user_hotel_activity.csv) 생성
# ============================================================

def generate_user_hotel_activity(
    users: pd.DataFrame,
    hotels: pd.DataFrame,
    n_events: int = N_ACTIVITIES,
) -> pd.DataFrame:
    """
    간단한 user-hotel activity 이벤트 생성
    - event_type: search, view, booking, rating
    - user_id / hotel_id 랜덤 매칭
    """
    if hotels.empty:
        raise RuntimeError("호텔 데이터가 비어 있습니다. 먼저 호텔을 생성해야 합니다.")

    event_types = ["search", "view", "booking", "rating"]
    trip_purposes = ["leisure", "business", "family", "friends"]
    source_channels = ["web", "app", "offline"]
    companions = ["solo", "couple", "family", "friends"]
    currencies = {
        "Paris": "EUR",
        "Seoul": "KRW",
        "Nairobi": "USD",
    }

    # signup 이후 ~ 오늘 사이의 이벤트로 가정
    now = datetime.now()
    min_signup = min(pd.to_datetime(users["signup_date"]))
    start_event_date = min_signup

    rows = []
    for event_id in range(1, n_events + 1):
        user = users.sample(1).iloc[0]
        hotel = hotels.sample(1).iloc[0]

        # 이벤트 시점
        event_ts = random_date(start_event_date, now)

        # 체크인/체크아웃 날짜 (이벤트 시점을 기준 ± 몇 일)
        stay_start = event_ts.date() + timedelta(days=random.randint(5, 60))
        nights = random.randint(1, 5)
        stay_end = stay_start + timedelta(days=nights)

        ev_type = random.choice(event_types)
        tp = random.choice(trip_purposes)
        comp = random.choice(companions)
        src = random.choice(source_channels)

        city = hotel["city"]
        currency = currencies.get(city, "USD")

        # 가격은 도시별 대략적인 범위에서 랜덤
        if city == "Seoul":
            price_per_night = random.randint(70000, 250000)
        elif city == "Paris":
            price_per_night = random.randint(120, 600)  # EUR
        else:  # Nairobi
            price_per_night = random.randint(50, 400)  # USD

        # booking / rating 에만 booking_id, rating_score 생성
        booking_id = None
        rating_score = None
        review_text = None

        if ev_type in ["booking", "rating"]:
            booking_id = f"bk_{event_id:06d}"

        if ev_type == "rating":
            rating_score = round(random.uniform(3.0, 5.0), 1)
            review_text = random.choice(
                [
                    "Great location and friendly staff.",
                    "Clean room but a bit noisy.",
                    "Very comfortable stay, would come again.",
                    "Average experience, nothing special.",
                    "Excellent value for money.",
                ]
            )

        row = {
            "event_id": event_id,
            "user_id": user["user_id"],
            "hotel_id": hotel["hotel_id"],
            "event_type": ev_type,
            "event_ts": event_ts.isoformat(),
            "checkin_date": stay_start,
            "checkout_date": stay_end,
            "num_nights": nights,
            "num_guests": random.randint(1, 4),
            "trip_purpose": tp,
            "companions": comp,
            "device_type": user["device_type"],
            "source_channel": src,
            "price_per_night": price_per_night,
            "currency": currency,
            "booking_id": booking_id,
            "rating_score": rating_score,
            "review_text": review_text,
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    return df


# ============================================================
# main: 전체 파이프라인 실행
# ============================================================

def main():
    # 1) 사용자 생성
    print("✅ Generating users...")
    users = generate_users(N_USERS)
    users_path = "users.csv"
    users.to_csv(users_path, index=False, encoding="utf-8-sig")
    print(f" -> {users_path} 생성 (rows={len(users)})")

    # 2) Google Maps 기반 호텔 생성
    print("✅ Initializing Google Maps client...")
    gmaps_client = init_google_maps_client()

    print("✅ Generating hotels from Google Maps Places API...")
    hotels = collect_hotels_from_google_maps(
        gmaps_client,
        target_cities=TARGET_CITIES,
        max_per_city=N_HOTELS_PER_CITY,
    )
    hotels_path = "hotels.csv"
    hotels.to_csv(hotels_path, index=False, encoding="utf-8-sig")
    print(f" -> {hotels_path} 생성 (rows={len(hotels)})")

    # 3) user-hotel activity 생성
    print("✅ Generating user-hotel activity events...")
    activities = generate_user_hotel_activity(users, hotels, N_ACTIVITIES)
    activities_path = "user_hotel_activity.csv"
    activities.to_csv(activities_path, index=False, encoding="utf-8-sig")
    print(f" -> {activities_path} 생성 (rows={len(activities)})")

    print("\n🎉 모든 CSV 생성 완료!")
    print(f" - {users_path}")
    print(f" - {hotels_path}")
    print(f" - {activities_path}")


if __name__ == "__main__":
    main()