from pathlib import Path
import random
import string
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from faker import Faker

# =========================
# 1. Parameters (scale)
# =========================
N_USERS = 100_000
N_PRODUCTS = 50_000
N_CAMPAIGNS = 500
N_EVENTS = 5_000_000

random.seed(42)
np.random.seed(42)

fake = Faker("fr_FR")  # 프랑스 로케일


# =========================
# 2. Util functions
# =========================
def random_date(start: datetime, end: datetime) -> datetime:
    delta = end - start
    rand_days = random.randrange(delta.days + 1)
    rand_seconds = random.randrange(24 * 3600)
    return start + timedelta(days=rand_days, seconds=rand_seconds)


def random_session_id():
    return "".join(random.choices(string.ascii_letters + string.digits, k=32))


# =========================
# 3. users generation (France)
# =========================

# 프랑스 행정구역(레지옹) 일부
regions = [
    "Île-de-France",
    "Auvergne-Rhône-Alpes",
    "Nouvelle-Aquitaine",
    "Occitanie",
    "Provence-Alpes-Côte d'Azur",
    "Hauts-de-France",
    "Grand Est",
    "Bretagne",
    "Normandie",
    "Pays de la Loire",
    "Centre-Val de Loire",
    "Bourgogne-Franche-Comté",
    "Corse",
]

device_types = ["mobile", "desktop", "tablet", "tv", "wearable"]
membership_levels = ["free", "bronze", "silver", "gold", "vip"]

# 카테고리는 프랑스어로, 키는 그대로 영어 (analytics용)
categories = [
    "jeux",  # gaming
    "shopping",
    "voyage",  # travel
    "vidéo",
    "musique",
    "livres",
    "éducation",
    "finance",
]

signup_start = datetime(2020, 1, 1)
signup_end = datetime(2025, 11, 1)

user_ids = np.arange(1, N_USERS + 1)

users = pd.DataFrame(
    {
        "user_id": user_ids,
        "name": [fake.name() for _ in range(N_USERS)],  # 프랑스식 이름
        "signup_date": [
            random_date(signup_start, signup_end).date() for _ in range(N_USERS)
        ],
        "gender": np.random.choice(["M", "F", "U"], size=N_USERS, p=[0.48, 0.48, 0.04]),
        "age": np.random.randint(18, 80, size=N_USERS),
        # 컬럼명은 state 유지, 값만 프랑스 레지옹
        "state": np.random.choice(regions, size=N_USERS),
        "device_type": np.random.choice(
            device_types, size=N_USERS, p=[0.6, 0.2, 0.1, 0.075, 0.025]  # 길이 5개 맞춤
        ),
        "membership_level": np.random.choice(
            membership_levels, size=N_USERS, p=[0.6, 0.15, 0.15, 0.07, 0.03]
        ),
        "preferred_category": np.random.choice(categories, size=N_USERS),
    }
)

print("users (FR) generated:", users.shape)


# =========================
# 4. products generation (France)
# =========================

category_mid_map = {
    "jeux": [
        "RPG",
        "casual",
        "tir",
        "puzzle",
        "sport",
        "stratégie",
        "aventure",
        "course",
        "simulation",
    ],
    "shopping": [
        "mode",
        "électronique",
        "alimentaire",
        "maison",
        "beauté",
        "bébé",
        "sport",
        "meubles",
        "loisirs",
        "animaux",
        "auto",
        "santé",
    ],
    "voyage": [
        "vol",
        "hôtel",
        "location_voiture",
        "tour",
        "croisière",
        "activité",
        "camping",
        "domestique",
        "international",
        "résort",
        "ville",
        "backpacking",
    ],
    "vidéo": [
        "film",
        "série",
        "divertissement",
        "animation",
        "documentaire",
        "webtoon",
        "clip_musical",
        "sport_en_direct",
        "infos",
        "éducation",
    ],
    "musique": [
        "pop",
        "rock",
        "hiphop",
        "jazz",
        "classique",
        "electro",
        "variété",
        "indé",
        "bande_originale",
    ],
    "livres": [
        "roman",
        "essai",
        "business",
        "informatique",
        "développement_perso",
        "sciences_humaines",
        "science",
        "art",
        "jeunesse",
        "bande_dessinée",
    ],
    "éducation": [
        "langue",
        "coding",
        "certificat",
        "loisir",
        "éducation_précoce",
        "cours_universitaire",
        "formation_pro",
        "cours_en_ligne",
        "mentorat",
    ],
    "finance": [
        "carte",
        "assurance",
        "prêt",
        "investissement",
        "retraite",
        "change",
        "immobilier",
        "gestion_actifs",
        "fiscalité",
        "comptabilité",
    ],
}

publisher_names = [
    "Studio Lumière",
    "Paris Games",
    "Boutique Hexagone",
    "Voyages Seine",
    "Cinéma Bleu",
    "Musique Parisienne",
    "Éditions du Rhône",
    "Académie Numérique",
    "Finance Hexagone",
    "Média Global",
    "Apprentissage Plus",
    "Capitale Créative",
    "Tech & Savoirs",
    "Monde Digital",
    "Rive Gauche Studio",
    "Montmartre Records",
    "Provence Books",
    "Bretagne Voyage",
    "Alpes Aventures",
    "Riviera Premium",
]

product_ids = np.arange(1, N_PRODUCTS + 1)
product_large = np.random.choice(categories, size=N_PRODUCTS)

product_mid = [np.random.choice(category_mid_map[cat]) for cat in product_large]


def make_product_name(cat_large, cat_mid, idx):
    base = {
        "jeux": "Pack",
        "shopping": "Offre Spéciale",
        "voyage": "Forfait",
        "vidéo": "Collection",
        "musique": "Sélection",
        "livres": "Série",
        "éducation": "Cours",
        "finance": "Solution",
    }.get(cat_large, "Produit")
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
            np.random.lognormal(mean=3.4, sigma=0.6, size=N_PRODUCTS) * 10, 0
        ),  # 유로 가정
        "publisher_name": np.random.choice(publisher_names, size=N_PRODUCTS),
        "release_date": [
            random_date(release_start, release_end).date() for _ in range(N_PRODUCTS)
        ],
        "is_active": np.random.choice([True, False], size=N_PRODUCTS, p=[0.85, 0.15]),
        "tags": [
            ",".join(
                np.random.choice(
                    [
                        "populaire",
                        "nouveau",
                        "promotion",
                        "événement",
                        "édition_limitée",
                        "recommandé",
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

print("products (FR) generated:", products.shape)


# =========================
# 5. campaigns generation (France)
# =========================

objectives = ["install", "reengage", "purchase", "awareness"]
campaign_ids = np.arange(1, N_CAMPAIGNS + 1)


def make_campaign_name(idx):
    return f"Campagne {idx} - {np.random.choice(['nouveaux utilisateurs', 'utilisateurs de retour', 'réachat'])}"


campaign_start_base = datetime(2022, 1, 1)
campaign_end_base = datetime(2025, 12, 31)

campaigns_data = []
for cid in campaign_ids:
    start = random_date(campaign_start_base, campaign_end_base - timedelta(days=30))
    end = start + timedelta(days=random.randint(7, 90))
    if end > campaign_end_base:
        end = campaign_end_base

    age_min = random.choice([18, 25, 35, 45])
    age_max = age_min + random.choice([10, 15, 20])

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
            "target_state": random.choice(["toutes-régions"] + regions),
            "target_category": random.choice(categories),
            "budget": float(np.round(np.random.uniform(50_000, 5_000_000), -2)),  # EUR
        }
    )

campaigns = pd.DataFrame(campaigns_data)
print("campaigns (FR) generated:", campaigns.shape)


# =========================
# 6. events generation (대규모)
# =========================

event_types = ["impression", "click", "install", "open", "purchase", "like"]
platforms = ["android", "ios", "web"]
traffic_sources = ["organic", "push", "search", "ad", "banner"]

event_start = datetime(2023, 1, 1)
event_end = datetime(2025, 11, 1)

user_sample = np.random.choice(user_ids, size=N_EVENTS)
product_sample = np.random.choice(product_ids, size=N_EVENTS)

campaign_sample = np.random.choice(
    np.append(campaign_ids, [np.nan] * int(N_CAMPAIGNS * 1.5)), size=N_EVENTS
)

event_type_sample = np.random.choice(
    event_types, size=N_EVENTS, p=[0.55, 0.20, 0.03, 0.10, 0.05, 0.07]
)

event_ts_sample = [random_date(event_start, event_end) for _ in range(N_EVENTS)]

platform_sample = np.random.choice(platforms, size=N_EVENTS, p=[0.6, 0.3, 0.1])
traffic_sample = np.random.choice(
    traffic_sources, size=N_EVENTS, p=[0.5, 0.1, 0.15, 0.2, 0.05]
)

position_sample = np.random.randint(1, 21, size=N_EVENTS)
session_ids = [random_session_id() for _ in range(N_EVENTS)]

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

print("events (FR) generated:", events.shape)


# =========================
# 7. Save to CSV
# =========================
assets_path = Path() / "assets"
assets_path.mkdir(parents=True, exist_ok=True)

users.to_csv(assets_path / "users-fr.csv", index=False)
products.to_csv(assets_path / "products-fr.csv", index=False)
campaigns.to_csv(assets_path / "campaigns-fr.csv", index=False)
events.to_csv(assets_path / "events-fr.csv", index=False)

print("CSV files saved:")
print("  users-fr.csv")
print("  products-fr.csv")
print("  campaigns-fr.csv")
print("  events-fr.csv")
