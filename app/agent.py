# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import json
from pathlib import Path

try:
    from a2ui.basic_catalog.provider import BasicCatalog
    from a2ui.schema.manager import A2uiSchemaManager
    HAS_A2UI = True
except ImportError:
    HAS_A2UI = False

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.adk.tools.tool_context import ToolContext
from google.cloud import firestore, storage
from google.genai import types

try:
    from .a2ui_utils import a2ui_callback
except ImportError:
    a2ui_callback = None

MODEL = "gemini-3.8-flash"
FIRESTORE_PROJECT_ID = "qwiklabs-gcp-03-81b834b64a12"
COLLECTION_NAME = "destinations"

# Lazy-loaded Firestore client with hardcoded project ID
_db: Optional[firestore.Client] = None


def get_firestore_client() -> firestore.Client:
    global _db
    if _db is None:
        _db = firestore.Client(project=FIRESTORE_PROJECT_ID)
    return _db


def list_destinations(
    category: Optional[str] = None,
    budget_tier: Optional[str] = None,
    max_daily_budget_usd: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """List travel destinations from Firestore with optional filtering.

    Args:
        category: Filter by travel category (e.g. 'Culture & Heritage', 'Nature & Adventure', 'Art & Culinary', 'Relaxation & Scenic').
        budget_tier: Filter by price tier ('$', '$$', '$$$', '$$$$').
        max_daily_budget_usd: Maximum daily estimated cost in USD.

    Returns:
        A list of matching destination items with details (name, city, country, coordinates, cost, highlights).
    """
    db = get_firestore_client()
    query = db.collection(COLLECTION_NAME)

    if category:
        query = query.where("category", "==", category)
    if budget_tier:
        query = query.where("budget_tier", "==", budget_tier)

    results = []
    for doc in query.stream():
        data = doc.to_dict()
        data["id"] = doc.id
        if max_daily_budget_usd is not None:
            daily_cost = data.get("estimated_daily_cost_usd", 0)
            if daily_cost > max_daily_budget_usd:
                continue
        results.append(data)

    return results


def get_destination_details(destination_id_or_name: str) -> Dict[str, Any]:
    """Retrieve detailed information for a specific destination by its ID, city, or name.

    Args:
        destination_id_or_name: The destination ID (e.g., 'kyoto-japan', 'banff-canada') or city name (e.g. 'Kyoto', 'Florence').

    Returns:
        A dictionary containing destination details, coordinates, highlights, and description.
    """
    db = get_firestore_client()
    search_term = destination_id_or_name.strip().lower()

    # Try direct doc ID match first
    doc_ref = db.collection(COLLECTION_NAME).document(search_term)
    doc = doc_ref.get()
    if doc.exists:
        data = doc.to_dict()
        data["id"] = doc.id
        return data

    # Fallback to search by city or name
    for doc in db.collection(COLLECTION_NAME).stream():
        data = doc.to_dict()
        data["id"] = doc.id
        city = str(data.get("city", "")).lower()
        name = str(data.get("name", "")).lower()
        if search_term in doc.id.lower() or search_term in city or search_term in name:
            return data

    return {"error": f"Destination matching '{destination_id_or_name}' not found."}


def save_destination(
    name: str,
    city: str,
    country: str,
    category: str,
    budget_tier: str,
    estimated_daily_cost_usd: float,
    highlights: List[str],
    description: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    best_season: Optional[str] = None,
) -> Dict[str, Any]:
    """Save or add a new travel destination recommendation to the Firestore catalog.

    Args:
        name: Name of the destination package or experience (e.g. 'Swiss Alps Scenic Rail').
        city: Destination city or region.
        country: Country name.
        category: Travel theme/category (e.g. 'Nature & Adventure', 'Culinary & Wine').
        budget_tier: Budget tier ('$', '$$', '$$$', '$$$$').
        estimated_daily_cost_usd: Estimated average daily cost per person in USD.
        highlights: List of key attractions or activities.
        description: Comprehensive summary of what makes this destination special.
        latitude: Latitude coordinate for mapping and route guidance.
        longitude: Longitude coordinate for mapping and route guidance.
        best_season: Optimal time of year to visit.

    Returns:
        A confirmation dictionary with the assigned destination ID and status.
    """
    db = get_firestore_client()
    doc_id = f"{city.strip().lower().replace(' ', '-')}-{country.strip().lower().replace(' ', '-')}"

    record = {
        "name": name,
        "city": city,
        "country": country,
        "category": category,
        "budget_tier": budget_tier,
        "estimated_daily_cost_usd": float(estimated_daily_cost_usd),
        "highlights": highlights,
        "description": description,
        "best_season": best_season or "All year round",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    if latitude is not None and longitude is not None:
        record["coordinates"] = {"lat": float(latitude), "lng": float(longitude)}

    db.collection(COLLECTION_NAME).document(doc_id).set(record, merge=True)
    return {"status": "success", "destination_id": doc_id, "message": f"Saved destination '{name}' successfully."}


def get_weather(query: str) -> str:
    """Get simulated weather forecast for a travel destination.

    Args:
        query: Destination city name.

    Returns:
        Weather report string.
    """
    q = query.lower()
    if "kyoto" in q:
        return "Kyoto: 65°F (18°C), clear skies with mild spring breeze."
    elif "banff" in q:
        return "Banff: 48°F (9°C), crisp mountain air with partly cloudy skies."
    elif "florence" in q:
        return "Florence: 72°F (22°C), sunny and warm, ideal for walking tours."
    elif "santorini" in q or "oia" in q:
        return "Santorini: 75°F (24°C), bright sun with gentle coastal winds."
    elif "cusco" in q:
        return "Cusco: 62°F (17°C), cool and dry mountain climate."
    return f"Simulated weather for {query}: 70°F (21°C), pleasant and mild travel conditions."


def get_route_guidance(origin: str, destination: str) -> Dict[str, Any]:
    """Look up real geographic coordinates, distance, and map navigation guidance between two places.

    Args:
        origin: Starting location, address, or landmark (e.g. 'Kyoto Station', 'Florence').
        destination: Target destination or attraction (e.g. 'Fushimi Inari Taisha', 'Pisa').

    Returns:
        A dictionary with origin/destination coordinates, distance in km and miles, estimated drive/transit time, and map URL.
    """
    import json
    import math
    import urllib.parse
    import urllib.request

    def geocode(place: str) -> Optional[Dict[str, Any]]:
        try:
            url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
                {"q": place, "format": "json", "limit": 1}
            )
            req = urllib.request.Request(url, headers={"User-Agent": "WanderlustTravelConcierge/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                if data:
                    return {
                        "name": data[0].get("display_name", place),
                        "lat": float(data[0]["lat"]),
                        "lng": float(data[0]["lon"]),
                    }
        except Exception:
            pass
        return None

    geo_orig = geocode(origin)
    geo_dest = geocode(destination)

    if not geo_orig or not geo_dest:
        return {"error": f"Could not resolve coordinates for '{origin}' or '{destination}'."}

    # Haversine distance
    r_km = 6371.0
    lat1, lon1 = math.radians(geo_orig["lat"]), math.radians(geo_orig["lng"])
    lat2, lon2 = math.radians(geo_dest["lat"]), math.radians(geo_dest["lng"])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    dist_km = round(r_km * c, 2)
    dist_miles = round(dist_km * 0.621371, 2)

    # Approximate travel time (assuming ~45 km/h urban/regional speed)
    est_hours = dist_km / 45.0
    est_minutes = int(est_hours * 60) if est_hours < 2 else None

    map_url = f"https://www.google.com/maps/dir/?api=1&origin={geo_orig['lat']},{geo_orig['lng']}&destination={geo_dest['lat']},{geo_dest['lng']}"

    return {
        "origin": geo_orig,
        "destination": geo_dest,
        "straight_line_distance_km": dist_km,
        "straight_line_distance_miles": dist_miles,
        "estimated_travel_time": f"{est_minutes} mins" if est_minutes else f"{round(est_hours, 1)} hours",
        "map_navigation_url": map_url,
    }


def convert_currency(amount: float, from_currency: str = "USD", to_currency: str = "EUR") -> Dict[str, Any]:
    """Convert travel budgets or costs between currencies using real-time exchange rates (via Frankfurter API).

    Args:
        amount: Amount of money to convert.
        from_currency: 3-letter currency code to convert from (e.g. 'USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD').
        to_currency: 3-letter currency code to convert to (e.g. 'JPY', 'EUR', 'GBP', 'CAD', 'AUD').

    Returns:
        A dictionary with the converted amount, exchange rate, and date of the rate.
    """
    import json
    import urllib.parse
    import urllib.request

    src = from_currency.strip().upper()
    dst = to_currency.strip().upper()

    if src == dst:
        return {"amount": amount, "from": src, "to": dst, "rate": 1.0, "converted_amount": amount}

    try:
        url = f"https://api.frankfurter.app/latest?from={urllib.parse.quote(src)}&to={urllib.parse.quote(dst)}"
        req = urllib.request.Request(url, headers={"User-Agent": "WanderlustTravelConcierge/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            rate = data.get("rates", {}).get(dst)
            if rate is not None:
                converted = round(amount * rate, 2)
                return {
                    "original_amount": amount,
                    "from_currency": src,
                    "to_currency": dst,
                    "exchange_rate": rate,
                    "converted_amount": converted,
                    "rate_date": data.get("date"),
                }
            return {"error": f"Currency code '{dst}' not supported or not found."}
    except Exception as e:
        return {"error": f"Failed to fetch exchange rates: {str(e)}"}


STORAGE_BUCKET_NAME = "wanderlust-travel-media-qwiklabs-gcp-03-81b834b64a12"
_storage_client: Optional[storage.Client] = None


def get_storage_client() -> storage.Client:
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
    return _storage_client


def generate_destination_image(
    prompt: str,
    destination_name: str,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """Generate a high-quality scenic photo or travel visual for a destination using gemini-3.1-flash-lite-image.

    The image is saved to the Playground's Artifacts panel and uploaded to Cloud Storage.

    Args:
        prompt: Descriptive prompt for generating the image (e.g. 'A scenic postcard of Fushimi Inari Taisha torii gates at sunset').
        destination_name: Name of the destination (e.g. 'Kyoto', 'Santorini').

    Returns:
        A dictionary with the public Cloud Storage URL, filename, and status.
    """
    import re
    import time
    from google import genai

    try:
        # Generate image using gemini-3.1-flash-lite-image in global region
        genai_client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT_ID, location="global")
        response = genai_client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
        )

        image_bytes = None
        for candidate in response.candidates:
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if part.inline_data and part.inline_data.data:
                        image_bytes = part.inline_data.data
                        break
            if image_bytes:
                break

        if not image_bytes:
            return {"error": "No image data was generated by the model."}

        # Filename sanitize
        slug = re.sub(r"[^a-zA-Z0-9_-]", "-", destination_name.strip().lower())
        timestamp = int(time.time())
        filename = f"{slug}-{timestamp}.jpg"

        # 1. Save artifact to Playground's Artifacts panel
        part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
        tool_context.save_artifact(filename=filename, artifact=part)

        # 2. Upload bytes directly to Cloud Storage bucket (no local file)
        storage_client = get_storage_client()
        bucket = storage_client.bucket(STORAGE_BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type="image/jpeg")

        public_url = f"https://storage.googleapis.com/{STORAGE_BUCKET_NAME}/{filename}"

        return {
            "status": "success",
            "destination": destination_name,
            "filename": filename,
            "public_image_url": public_url,
            "message": f"Generated image for {destination_name} and published to Cloud Storage.",
        }
    except Exception as e:
        return {"error": f"Image generation failed: {str(e)}"}


# Load Agent Engine resource name from deployment_metadata.json
def _get_agent_engine_resource_name() -> Optional[str]:
    metadata_path = Path(__file__).resolve().parent.parent / "deployment_metadata.json"
    if metadata_path.exists():
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("remote_agent_runtime_id")
        except Exception:
            pass
    return "projects/183374071774/locations/us-east1/reasoningEngines/1224111583970459648"


agent_engine_resource = _get_agent_engine_resource_name()
code_executor = (
    AgentEngineSandboxCodeExecutor(agent_engine_resource_name=agent_engine_resource)
    if agent_engine_resource
    else None
)


async def generate_memories_callback(callback_context: CallbackContext):
    """Write session events to Vertex AI Memory Bank for long-term user memory extraction."""
    await callback_context.add_session_to_memory()
    return None


BASE_INSTRUCTION = """You are Wanderlust, an intelligent and inspiring travel concierge agent.
Your mission is to help travelers discover destinations, plan customized itineraries, navigate map routes, and curate travel recommendations.

Memory & Personalization:
- You have cross-session long-term memory powered by Vertex AI Memory Bank.
- ALWAYS remember and respect all stated user preferences, including travel style (luxury, backpacking, adventure), budget limits, dietary restrictions, past visited cities, companions, and transportation choices.
- Actively acknowledge relevant past preferences when making recommendations.

Available Tools:
- list_destinations: Explore or filter destinations by category, budget tier, or daily cost limit.
- get_destination_details: Fetch complete destination records, coordinates, and highlights.
- save_destination: Add new or traveler-recommended destinations to the catalog.
- get_route_guidance: Fetch real coordinates, distances, travel times, and map navigation links between any two places.
- convert_currency: Convert travel budgets and daily expenses between world currencies using live exchange rates.
- generate_destination_image: Create stunning travel postcards/photos using gemini-3.1-flash-lite-image, saved to artifacts and Cloud Storage.
- get_weather: Check weather forecasts for travel planning.
- Code execution sandbox: You can run Python code directly in a secure sandbox to calculate complex travel budgets, route optimizations, or custom data analysis.

Always be friendly, structured, and informative. When recommending destinations or creating itineraries, offer to generate visuals or postcards to bring the trip to life."""

if HAS_A2UI:
    schema_manager = A2uiSchemaManager(
        version="0.8",
        catalogs=[BasicCatalog.get_config("0.8")],
    )

    instruction = schema_manager.generate_system_prompt(
        role_description=BASE_INSTRUCTION,
        workflow_description="Analyze the user request, call necessary tools, and return structured A2UI cards for destination recommendations, itineraries, routes, and travel visuals.",
        ui_description=(
            "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
            "Never nest a Card inside a Card. "
            "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
            "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
            "nothing in adk web). "
            "You may include one Image component, but only when you have a public https "
            "URL for the image (for example the public_image_url returned by generate_destination_image). "
            "Set the Image url to that exact https link, for example "
            '{"Image": {"url": {"literalString": "https://storage.googleapis.com/..."}}}. '
            "Never point an Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
            "not have a public URL, add a short Text line noting the image instead. "
            "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for headings and emphasis. "
            "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
            "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
        ),
        include_schema=True,
        include_examples=True,
    )
    model_callback = a2ui_callback
else:
    instruction = BASE_INSTRUCTION
    model_callback = None


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    tools=[
        PreloadMemoryTool(),
        list_destinations,
        get_destination_details,
        save_destination,
        get_route_guidance,
        convert_currency,
        generate_destination_image,
        get_weather,
    ],
    code_executor=code_executor,
    after_model_callback=model_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
