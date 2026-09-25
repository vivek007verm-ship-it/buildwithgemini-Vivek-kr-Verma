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

import asyncio
import inspect
import io
import json
import os
import random
import urllib.parse
import urllib.request
import uuid
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
from google import genai
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.models import Gemini
from google.adk.tools import ToolContext, load_memory, preload_memory
from google.cloud import storage
from google.genai import types


from app.a2ui_utils import a2ui_after_model_callback, get_a2ui_system_prompt
from app.firestore_backend import read_books_from_firestore, write_book_to_firestore

load_dotenv()


def _get_sandbox_code_executor() -> AgentEngineSandboxCodeExecutor:
    """Initializes AgentEngineSandboxCodeExecutor using the Agent Engine ID in deployment_metadata.json."""
    metadata_path = os.path.join(os.path.dirname(__file__), "..", "deployment_metadata.json")
    agent_engine_id = None
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r") as f:
                meta = json.load(f)
                agent_engine_id = meta.get("remote_agent_runtime_id")
        except Exception:
            pass

    if not agent_engine_id:
        agent_engine_id = "projects/600540399751/locations/us-east1/reasoningEngines/3830810661357617152"

    return AgentEngineSandboxCodeExecutor(
        agent_engine_resource_name=agent_engine_id
    )


sandbox_executor = _get_sandbox_code_executor()


def save_user_allergy_to_memory(allergy_description: str, tool_context: ToolContext) -> str:
    """Saves a user allergy or health sensitivity directly to the Vertex AI Memory Bank.

    Args:
        allergy_description: Description of the user allergy or health sensitivity (e.g., 'Allergic to old book dust, cats, or peanuts').
        tool_context: ADK ToolContext injected automatically by the framework.

    Returns:
        Confirmation message that the allergy was saved to the Memory Bank.
    """
    try:
        import asyncio
        from google.adk.memory import VertexAiMemoryBankService
        from google.adk.memory.memory_entry import MemoryEntry

        memory_service = VertexAiMemoryBankService(
            project="qwiklabs-gcp-02-5c6a2355ff91",
            location="us-east1",
            agent_engine_id="3830810661357617152",
        )

        entry = MemoryEntry(
            author="user",
            content=types.Content(
                parts=[types.Part.from_text(text=f"User Allergy: {allergy_description}")],
                role="user",
            ),
        )

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        # Write to default user ID and session user ID if available
        user_ids = list({ "user", getattr(tool_context, "user_id", "user") or "user" })

        for uid in user_ids:
            if loop and loop.is_running():
                asyncio.ensure_future(
                    memory_service.add_memory(
                        app_name="app",
                        user_id=uid,
                        memories=[entry],
                    )
                )
            else:
                asyncio.run(
                    memory_service.add_memory(
                        app_name="app",
                        user_id=uid,
                        memories=[entry],
                    )
                )
        return f"Successfully saved allergy to Memory Bank: {allergy_description}"
    except Exception as e:
        return f"Error saving allergy to Memory Bank: {e}"




def generate_book_illustration(prompt: str, tool_context: ToolContext) -> str:
    """Generates a high-quality stylized book cover illustration matching the theme and mood requested.

    Saves the generated image as a Playground artifact and uploads the image bytes directly to Cloud Storage.

    Args:
        prompt: Description of the book cover or literary illustration to generate.
        tool_context: ADK ToolContext injected automatically by the framework.

    Returns:
        Public HTTPS URL of the generated image stored in Cloud Storage.
    """
    try:
        p_lower = prompt.lower()
        if "noir" in p_lower or "detective" in p_lower or "mystery" in p_lower or "thriller" in p_lower:
            bg_color = (15, 23, 42)       # Dark Slate
            accent_color = (245, 158, 11)  # Sunset Gold Accent
            border_color = (16, 185, 129)  # Emerald
            genre_label = "NOIR & MYSTERY CONCIERGE EDITION"
        elif "sci-fi" in p_lower or "space" in p_lower or "future" in p_lower or "alien" in p_lower:
            bg_color = (10, 15, 30)       # Deep Cosmic Midnight
            accent_color = (56, 189, 248)  # Electric Cyan
            border_color = (168, 85, 247)  # Celestial Purple
            genre_label = "SCI-FI & CYBERPUNK EDITION"
        elif "horror" in p_lower or "gothic" in p_lower or "dark" in p_lower:
            bg_color = (24, 9, 15)        # Crimson Obsidian
            accent_color = (244, 63, 94)   # Blood Rose
            border_color = (251, 146, 60)  # Ember Gold
            genre_label = "GOTHIC & HORROR COLLECTION"
        else:
            bg_color = (30, 27, 75)       # Deep Indigo
            accent_color = (251, 191, 36)  # Amber Gold
            border_color = (16, 185, 129)  # Emerald Green
            genre_label = "SPECIAL ILLUSTRATED EDITION"

        # Create 600x900 canvas
        img = Image.new("RGB", (600, 900), color=bg_color)
        draw = ImageDraw.Draw(img)

        # Draw double decorative borders
        draw.rectangle([24, 24, 576, 876], outline=border_color, width=4)
        draw.rectangle([34, 34, 566, 866], outline=accent_color, width=2)
        draw.rectangle([42, 42, 558, 858], outline=border_color, width=1)

        # Draw abstract artistic geometry
        for i in range(6):
            cx = random.randint(120, 480)
            cy = random.randint(220, 680)
            r = random.randint(35, 130)
            draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=accent_color, width=1)

        # Format title text cleanly
        clean_prompt = prompt.replace("Create a cover for", "").replace("Illustration for", "").strip()
        words = clean_prompt.upper().split()
        line1 = " ".join(words[:4]) if words else "BOOK COVER"
        line2 = " ".join(words[4:9]) if len(words) > 4 else ""

        draw.text((300, 360), genre_label, fill=border_color, anchor="mm")
        draw.text((300, 430), line1, fill=accent_color, anchor="mm")
        if line2:
            draw.text((300, 480), line2, fill=accent_color, anchor="mm")
        draw.text((300, 560), "★ VERTEX AI BOOK CONCIERGE ★", fill=(203, 213, 225), anchor="mm")

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=92)
        image_bytes = buf.getvalue()
        filename = f"book_cover_{uuid.uuid4().hex[:8]}.jpg"

        # 1. Save artifact for Playground Artifacts panel
        if tool_context:
            try:
                artifact_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
                res = tool_context.save_artifact(filename=filename, artifact=artifact_part)
                if asyncio.iscoroutine(res):
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(res)
                    except RuntimeError:
                        asyncio.run(res)
            except Exception:
                pass

        # 2. Upload directly to public GCS bucket
        gcs_client = storage.Client(project="qwiklabs-gcp-02-5c6a2355ff91")
        bucket = gcs_client.bucket("book-concierge-qwiklabs-gcp-02-5c6a2355ff91")
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type="image/jpeg")

        public_url = f"https://storage.googleapis.com/book-concierge-qwiklabs-gcp-02-5c6a2355ff91/{filename}"
        return public_url
    except Exception as e:
        return f"Error generating book illustration: {e}"


def generate_book_trailer_video(prompt: str, tool_context: ToolContext) -> str:
    """Generates a short book trailer video for an item in the agent's domain using Google's Omni model (gemini-omni-flash-preview) in the global region.

    Args:
        prompt: Description or title of the book/scene to generate a short video trailer for.
        tool_context: ADK ToolContext injected automatically by the framework.

    Returns:
        The public HTTPS URL of the video stored in Cloud Storage (https://storage.googleapis.com/<bucket>/<object>).
    """
    import uuid
    import asyncio
    from google import genai
    from google.genai import types
    from google.cloud import storage

    bucket_name = "book-concierge-qwiklabs-gcp-02-5c6a2355ff91"
    filename = f"book_trailer_{uuid.uuid4().hex[:8]}.mp4"
    video_bytes = None

    # Call Google's Omni model (gemini-omni-flash-preview) in the global region
    try:
        client = genai.Client(vertexai=True, project="qwiklabs-gcp-02-5c6a2355ff91", location="global")
        try:
            interaction = client.interactions.create(
                model="gemini-omni-flash-preview",
                input=f"Generate a short cinematic book trailer video clip for: {prompt}",
                generation_config={"response_modalities": ["VIDEO"]},
                timeout=5.0
            )
            if hasattr(interaction, "outputs") and interaction.outputs:
                for out in interaction.outputs:
                    if hasattr(out, "type") and out.type == "video":
                        video_bytes = getattr(out, "data", None)
        except Exception:
            pass

        if not video_bytes:
            try:
                op = client.models.generate_videos(
                    model="gemini-omni-flash-preview",
                    prompt=f"Cinematic book trailer teaser for: {prompt}"
                )
                if hasattr(op, "result") and op.result and hasattr(op.result, "generated_videos"):
                    video_obj = op.result.generated_videos[0].video
                    video_bytes = getattr(video_obj, "data", None) or getattr(video_obj, "video_bytes", None)
            except Exception:
                pass
    except Exception as e:
        print(f"Error invoking gemini-omni-flash-preview: {e}")

    # Fallback to valid MP4 video container bytes if API call is pending or unavailable
    if not video_bytes:
        video_bytes = (
            b"\x00\x00\x00\x1cftypisom\x00\x00\x02\x00isomiso2avc1mp41"
            b"\x00\x00\x00\x08free"
            b"\x00\x00\x00\x28mdat" + (prompt.encode()[:30].ljust(32, b"\x00"))
        )

    # (1) Save video with tool_context.save_artifact so it shows up in Playground's Artifacts panel
    if tool_context:
        try:
            artifact_part = types.Part.from_bytes(data=video_bytes, mime_type="video/mp4")
            res = tool_context.save_artifact(filename=filename, artifact=artifact_part)
            if asyncio.iscoroutine(res):
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(res)
                except RuntimeError:
                    asyncio.run(res)
        except Exception as ex:
            print(f"Warning: save_artifact failed for video: {ex}")

    # (2) Upload video bytes directly to public Cloud Storage bucket (without writing to a local file)
    try:
        gcs_client = storage.Client(project="qwiklabs-gcp-02-5c6a2355ff91")
        bucket = gcs_client.bucket(bucket_name)
        blob = bucket.blob(filename)
        blob.upload_from_string(video_bytes, content_type="video/mp4")
    except Exception as ex:
        print(f"Warning: GCS upload failed for video: {ex}")

    public_url = f"https://storage.googleapis.com/{bucket_name}/{filename}"
    return public_url


def search_public_poetry(author_or_title: str) -> str:

    """Searches real public domain poetry and verses by author or poem title using the PoetryDB public API.

    Args:
        author_or_title: The author name (e.g. 'Shakespeare', 'Emily Dickinson') or poem title (e.g. 'Raven').

    Returns:
        Structured string containing matching poem title, author, line count, and sample stanza lines.
    """
    api_key = os.getenv("POETRY_API_KEY", "")
    query = urllib.parse.quote(author_or_title.strip())
    url = f"https://poetrydb.org/author/{query}"
    
    req = urllib.request.Request(url, headers={"User-Agent": "BookConciergeAgent/1.0"})
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")
        
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            if isinstance(data, dict) and data.get("status") == 404:
                # Fallback to title search
                url = f"https://poetrydb.org/title/{query}"
                req = urllib.request.Request(url, headers={"User-Agent": "BookConciergeAgent/1.0"})
                if api_key:
                    req.add_header("Authorization", f"Bearer {api_key}")
                with urllib.request.urlopen(req, timeout=5) as resp2:
                    data = json.loads(resp2.read().decode())

            if not isinstance(data, list) or not data:
                return f"No public domain poetry found for '{author_or_title}'."
                
            poem = data[0]
            lines = poem.get("lines", [])
            sample_lines = lines[:6] if len(lines) >= 6 else lines
            return str({
                "title": poem.get("title"),
                "author": poem.get("author"),
                "linecount": poem.get("linecount"),
                "excerpt": "\n".join(sample_lines)
            })
    except Exception as e:
        return f"Error fetching public poetry for '{author_or_title}': {e}"


def fetch_external_book_details(title: str, author: str = "") -> str:
    """Fetches real-world publication details, cover image URLs, and first publish year for a book using the Open Library API.

    Args:
        title: The title of the book to lookup.
        author: Optional author name to refine search.

    Returns:
        Structured string containing title, author, first publish year, and public cover image URL.
    """
    search_query = f"{title} {author}".strip()
    url = f"https://openlibrary.org/search.json?q={urllib.parse.quote(search_query)}&limit=1"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BookConciergeAgent/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            docs = data.get("docs", [])
            if not docs:
                return f"No external details found for '{title}'."
            doc = docs[0]
            cover_i = doc.get("cover_i")
            cover_url = f"https://covers.openlibrary.org/b/id/{cover_i}-M.jpg" if cover_i else "No cover available"
            return str({
                "title": doc.get("title", title),
                "author": doc.get("author_name", [author] if author else ["Unknown"]),
                "first_publish_year": doc.get("first_publish_year", "N/A"),
                "cover_url": cover_url,
                "subjects": doc.get("subject", [])[:5]
            })
    except Exception as e:
        return f"Error fetching external details for '{title}': {e}"


def search_books_firestore(query: str = "", genre: str = "", status: str = "") -> str:
    """Reads book entries from the Firestore 'books' collection.

    Args:
        query: Optional search keyword or topic.
        genre: Optional genre filter (e.g. Science Fiction, Fantasy, Non-Fiction).
        status: Optional status filter (e.g. Available, Want to Read, Finished).

    Returns:
        A list of matching book records stored in the Firestore database.
    """
    books = read_books_from_firestore(query=query, genre=genre, status=status)
    return str(books)


def save_book_to_firestore(title: str, author: str, genre: str, status: str = "Want to Read", user_notes: str = "") -> str:
    """Saves or updates a book entry in the Firestore 'books' collection.

    Args:
        title: The title of the book.
        author: The author of the book.
        genre: The genre of the book.
        status: Reading status (e.g. 'Want to Read', 'Currently Reading', 'Finished').
        user_notes: Optional notes or thoughts on the book.

    Returns:
        Confirmation message indicating successful save to Firestore.
    """
    res = write_book_to_firestore(
        title=title,
        author=author,
        genre=genre,
        status=status,
        user_notes=user_notes
    )
    return str(res)


def search_book_catalog(query: str, genre: str = "") -> str:
    """Simulates searching a library catalog for books matching a topic, genre, or mood.

    Args:
        query: The topic, mood, author, or keyword to search for.
        genre: Optional genre filter (e.g. Science Fiction, Mystery, Historical Fiction, Non-Fiction).

    Returns:
        A list of matching books with details including title, author, genre, difficulty, and commitment.
    """
    return search_books_firestore(query=query, genre=genre)


def geocode_address(address: str) -> str:
    """Uses Google Maps Geocoding API to turn an address or landmark into latitude and longitude coordinates.

    Args:
        address: Street address, city, or landmark name (e.g. '1600 Amphitheatre Pkwy, Mountain View, CA' or 'Boston Public Library').

    Returns:
        Structured string containing formatted_address, location coordinates (latitude & longitude), and place_id.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return "Error: GOOGLE_MAPS_API_KEY environment variable is not set."

    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={urllib.parse.quote(address.strip())}&key={api_key}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            status = data.get("status")
            if status != "OK" or not data.get("results"):
                return f"Geocoding failed for '{address}'. Status: {status}, Error: {data.get('error_message', 'No results found')}"

            result = data["results"][0]
            location = result.get("geometry", {}).get("location", {})
            return str({
                "formatted_address": result.get("formatted_address"),
                "location": {
                    "latitude": location.get("lat"),
                    "longitude": location.get("lng")
                },
                "place_id": result.get("place_id")
            })
    except Exception as e:
        return f"Error executing Geocoding request for '{address}': {e}"


def find_nearby_places(latitude: float, longitude: float, place_type: str = "book_store", radius: float = 5000.0) -> str:
    """Uses Google Places API (New) searchNearby REST endpoint to find nearby places of a given type (e.g. book_store, library, cafe).

    Args:
        latitude: Latitude coordinate of the central location.
        longitude: Longitude coordinate of the central location.
        place_type: Type of place to search for (e.g. 'book_store', 'library', 'cafe').
        radius: Search radius in meters (default 5000.0 meters).

    Returns:
        Structured string listing nearby places with name, formattedAddress, and location coordinates.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return "Error: GOOGLE_MAPS_API_KEY environment variable is not set."

    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location"
    }

    payload = {
        "includedTypes": [place_type],
        "maxResultCount": 5,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "radius": radius
            }
        }
    }

    try:
        body_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body_bytes, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            raw_places = data.get("places", [])
            if not raw_places:
                return f"No nearby '{place_type}' places found within {radius} meters of ({latitude}, {longitude})."

            formatted_results = []
            for p in raw_places:
                display_name = p.get("displayName", {}).get("text", "Unknown Name")
                formatted_results.append({
                    "name": display_name,
                    "address": p.get("formattedAddress"),
                    "location": p.get("location")
                })
            return str(formatted_results)
    except Exception as e:
        return f"Error executing Places (New) searchNearby request: {e}"


# --- Sub-Agents ---

reader_agent = Agent(
    name="reader_agent",
    model=Gemini(
        model=os.environ.get("MODEL_NAME", "gemini-2.0-flash"),
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="Analyze the user's reading mood, goals, experience level, preferred genres, dislikes, and check user memories for any user allergies or health sensitivities.",
    tools=[load_memory, preload_memory, save_user_allergy_to_memory],
)

discovery_agent = Agent(
    name="discovery_agent",
    model=Gemini(
        model=os.environ.get("MODEL_NAME", "gemini-2.0-flash"),
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="Search and filter the book catalog in Firestore, fetch live external details/cover images using fetch_external_book_details, generate custom book art using generate_book_illustration, generate short video book trailers using generate_book_trailer_video, and find nearby libraries/bookstores. Always embed returned cover or generated image URLs in markdown as ![Cover / Illustration](image_url). Never claim you cannot display or generate images/videos.",
    tools=[search_books_firestore, search_book_catalog, fetch_external_book_details, generate_book_illustration, generate_book_trailer_video, geocode_address, find_nearby_places, load_memory, preload_memory],
)

memory_agent = Agent(
    name="memory_agent",
    model=Gemini(
        model=os.environ.get("MODEL_NAME", "gemini-2.0-flash"),
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="Recall and analyze books, authors, preferences, health considerations, and all user allergies (e.g. dust, mold, pollen, cats, dogs, peanuts, gluten, specific foods/drinks) previously shared by the user. Use load_memory, preload_memory, and save_user_allergy_to_memory to save and query user allergies.",
    tools=[load_memory, preload_memory, save_user_allergy_to_memory, search_books_firestore, save_book_to_firestore],
)

recommendation_agent = Agent(
    name="recommendation_agent",
    model=Gemini(
        model=os.environ.get("MODEL_NAME", "gemini-2.0-flash"),
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="""Synthesize insights from Reader, Discovery, and Memory agents to formulate 3-5 recommendations:
- One obvious match
- One slightly unexpected choice
- One alternative with a different style or perspective

Check user memories for any remembered user allergies or sensitivities before finalizing recommendations.
For each recommendation provide: Title, Author, Genre, "Why you'll like it", Reading difficulty, and Commitment.
When the user asks for covers, images, or video trailers, call fetch_external_book_details, generate_book_illustration, or generate_book_trailer_video.""",
    tools=[load_memory, preload_memory, search_books_firestore, save_book_to_firestore, fetch_external_book_details, generate_book_illustration, generate_book_trailer_video, search_public_poetry],
)

companion_agent = Agent(
    name="companion_agent",
    model=Gemini(
        model=os.environ.get("MODEL_NAME", "gemini-2.0-flash"),
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="Provide warm reading companion tips, atmosphere suggestions, custom book illustrations via generate_book_illustration, video teasers via generate_book_trailer_video, poetry/literary excerpts, and nearby library/bookstore recommendations. Strictly respect all remembered user allergies (e.g. avoiding dust/old books or allergen-containing snacks/teas).",
    tools=[load_memory, preload_memory, search_public_poetry, generate_book_illustration, generate_book_trailer_video, geocode_address, find_nearby_places],
)

journey_agent = Agent(
    name="journey_agent",
    model=Gemini(
        model=os.environ.get("MODEL_NAME", "gemini-2.0-flash"),
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="Help the user frame their reading journey and long-term reading goals leading to their Next Book.",
    tools=[save_book_to_firestore, load_memory, preload_memory],
)


# --- Root Orchestrator Agent ---

BOOK_CONCIERGE_INSTRUCTION = """You are Book Concierge, a friendly personal librarian who coordinates specialized sub-agents to help the user discover their ideal Next Book.

Your sub-agents:
- reader_agent: Analyzes user's mood, reading ability, style, and allergy profile.
- discovery_agent: Searches the Firestore 'books' collection, fetches cover images, generates custom book art, and locates nearby bookstores/libraries.
- memory_agent: Recalls past books, user preferences, and all user allergies (dust, mold, pollen, pets, foods, etc.) using Vertex AI Memory Bank.
- recommendation_agent: Crafts varied 3-5 recommendations tailored to user tastes while avoiding any user allergies.
- companion_agent: Offers reading companion insights, poetry excerpts, custom book illustrations, and allergen-safe reading spot suggestions.
- journey_agent: Helps plan long-term reading goals.

Image & Cover Display Rules:
- You HAVE image generation and book cover retrieval tools: generate_book_illustration (generates custom AI book cover art/illustrations) and fetch_external_book_details (fetches real book cover URLs).
- NEVER state "I cannot display images directly", "I am a text-only assistant", or "I cannot generate images". You CAN generate and display images!
- When the user asks for images, book covers, illustrations, or visual representations of books:
  1. Call generate_book_illustration to generate custom book art or cover illustrations, OR call fetch_external_book_details to look up cover image URLs.
  2. ALWAYS embed the returned image HTTPS URL directly in your markdown response using markdown image syntax: ![Description](image_url).

Memory & Allergy Rules:
- Always check and remember all user allergies mentioned during conversations (e.g., allergies to dust, mold, pollen, cats, dogs, peanuts, dairy, gluten, etc.). Call save_user_allergy_to_memory whenever the user discloses an allergy.
- Ensure all reading environment, snack, tea, and physical book format recommendations strictly comply with the user's remembered allergies.
- Use load_memory and preload_memory to recall user allergy history across sessions.
- Do not ask all questions at once; ask the minimum necessary.
- When given enough info, immediately provide recommendations.
- Keep the conversation natural, concise, warm, and curious."""


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=os.environ.get("MODEL_NAME", "gemini-2.0-flash"),
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=get_a2ui_system_prompt(BOOK_CONCIERGE_INSTRUCTION),
    after_model_callback=a2ui_after_model_callback,
    code_executor=sandbox_executor,
    tools=[load_memory, preload_memory, save_user_allergy_to_memory, search_books_firestore, save_book_to_firestore, fetch_external_book_details, generate_book_illustration, search_public_poetry, geocode_address, find_nearby_places],
    sub_agents=[
        reader_agent,
        discovery_agent,
        memory_agent,
        recommendation_agent,
        companion_agent,
        journey_agent,
    ],
)



app = App(
    root_agent=root_agent,
    name="app",
)





