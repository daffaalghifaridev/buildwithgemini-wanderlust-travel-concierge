"""Seed script for Wanderlust Travel Concierge Firestore collection."""

from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-03-81b834b64a12"
COLLECTION_NAME = "destinations"

SEEDED_DESTINATIONS = [
    {
        "id": "kyoto-japan",
        "name": "Kyoto Cultural Journey",
        "city": "Kyoto",
        "country": "Japan",
        "category": "Culture & Heritage",
        "budget_tier": "$$$",
        "estimated_daily_cost_usd": 180,
        "coordinates": {"lat": 35.0116, "lng": 135.7681},
        "highlights": ["Fushimi Inari Taisha", "Kinkaku-ji (Golden Pavilion)", "Arashiyama Bamboo Grove"],
        "best_season": "Spring (Cherry Blossom) & Autumn",
        "description": "Historic imperial capital famous for classical Buddhist temples, gardens, imperial palaces, Shinto shrines and traditional wooden houses.",
    },
    {
        "id": "banff-canada",
        "name": "Banff Alpine Wilderness",
        "city": "Banff",
        "country": "Canada",
        "category": "Nature & Adventure",
        "budget_tier": "$$",
        "estimated_daily_cost_usd": 150,
        "coordinates": {"lat": 51.1784, "lng": -115.5708},
        "highlights": ["Lake Louise", "Moraine Lake", "Banff Gondola", "Johnston Canyon"],
        "best_season": "Summer (Hiking) & Winter (Skiing)",
        "description": "Pristine national park nestled in the Canadian Rockies with turquoise glacial lakes, towering peaks, and abundant wildlife.",
    },
    {
        "id": "florence-italy",
        "name": "Florence Renaissance Discovery",
        "city": "Florence",
        "country": "Italy",
        "category": "Art & Culinary",
        "budget_tier": "$$",
        "estimated_daily_cost_usd": 160,
        "coordinates": {"lat": 43.7696, "lng": 11.2558},
        "highlights": ["Uffizi Gallery", "Duomo (Santa Maria del Fiore)", "Ponte Vecchio", "Tuscan Wine Tour"],
        "best_season": "Spring & Autumn",
        "description": "The cradle of the Renaissance, renowned for masterpieces of art and architecture, charming cobblestone streets, and Tuscan culinary delicacies.",
    },
    {
        "id": "oia-santorini",
        "name": "Santorini Coastal Escape",
        "city": "Oia",
        "country": "Greece",
        "category": "Relaxation & Scenic",
        "budget_tier": "$$$$",
        "estimated_daily_cost_usd": 250,
        "coordinates": {"lat": 36.4618, "lng": 25.3753},
        "highlights": ["Caldera Sunset Views", "Amoudi Bay", "Red Beach", "Akrotiri Ruins"],
        "best_season": "Late Spring to Early Autumn",
        "description": "Postcard-perfect Aegean island with whitewashed cliffside villas, cobalt-blue domes, dramatic caldera panoramas, and world-class sunsets.",
    },
    {
        "id": "cusco-peru",
        "name": "Cusco & Machu Picchu Expedition",
        "city": "Cusco",
        "country": "Peru",
        "category": "Adventure & History",
        "budget_tier": "$$",
        "estimated_daily_cost_usd": 110,
        "coordinates": {"lat": -13.5319, "lng": -71.9675},
        "highlights": ["Machu Picchu Citadel", "Sacred Valley", "Rainbow Mountain", "Plaza de Armas"],
        "best_season": "May to October (Dry Season)",
        "description": "Ancient Inca empire capital nestled in the Andes mountains, serving as the gateway to the sacred ruins of Machu Picchu.",
    },
]


def seed():
    print(f"Connecting to Firestore using project ID: '{PROJECT_ID}'...")
    db = firestore.Client(project=PROJECT_ID)
    batch = db.batch()

    for item in SEEDED_DESTINATIONS:
        doc_ref = db.collection(COLLECTION_NAME).document(item["id"])
        data = {k: v for k, v in item.items() if k != "id"}
        batch.set(doc_ref, data)

    batch.commit()
    print(f"Successfully seeded {len(SEEDED_DESTINATIONS)} items into '{COLLECTION_NAME}' collection!")


if __name__ == "__main__":
    seed()
