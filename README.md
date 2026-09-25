# buildwithgemini-Vivek kr Verma — AI Personal Librarian

> An intelligent, multi-agent reading assistant built with the Google Agent Development Kit (ADK), Vertex AI Reasoning Engine, Firestore, Memory Bank, Cloud Storage, and Gemini models.

![Book Concierge Demo](demo.gif)

---

## 🌟 Overview

**Book Concierge** is an AI-powered personal librarian that coordinates specialized sub-agents to help users discover, explore, and organize their ideal reading journeys. It combines personalized recommendations, real-time memory recall (including user preferences and allergy constraints), physical bookstore location lookup, custom cover art generation, and video trailers into a unified chat interface.

---

## 🏗 Architecture & Google Cloud Services

Book Concierge is built using the **Agent Development Kit (ADK)** and leverages the following Google Cloud services and APIs:

| Component / Service | Description & Integration |
| :--- | :--- |
| **Vertex AI Reasoning Engine** | Hosts and orchestrates the root agent and multi-agent hierarchy (`reader_agent`, `discovery_agent`, `memory_agent`, `recommendation_agent`, `companion_agent`, `journey_agent`). |
| **Vertex AI Memory Bank** | Manages persistent user memories across conversations via `preload_memory` and `load_memory`, automatically tracking user tastes, mood, and health/allergy constraints. |
| **Google Cloud Firestore** | Stores book catalog documents and user reading lists (`search_books_firestore`, `save_book_to_firestore`). |
| **Google Cloud Storage (GCS)** | Public storage bucket (`book-concierge-qwiklabs-gcp-02-5c6a2355ff91`) hosting dynamically generated book cover artwork, illustrations, and video trailers. |
| **Google GenAI / Omni Models** | Generates custom 600x900 book illustrations (`generate_book_illustration`) and short video trailers (`generate_book_trailer_video`) using `gemini-omni-flash-preview` in the `global` region. |
| **Google Maps Places (New) API** | Performs geocoding and proximity searches for nearby physical bookstores and libraries (`geocode_address`, `find_nearby_places`). |
| **A2UI Protocol** | Implements the Declarative UI protocol (`A2uiSchemaManager`) and `after_model_callback` for rich UI components. |
| **External APIs** | Integrated with Open Library API (`fetch_external_book_details`) and PoetryDB API (`search_public_poetry`). |

---

## 📋 Features

- 📚 **Personalized Book Discovery**: Multi-agent consensus generating 3–5 tailored recommendations (obvious match, unexpected choice, and stylistic alternative).
- 🧠 **Persistent Allergy & Preference Memory**: Automatically checks and honors user health/allergy profiles (e.g. dust, mold, food/tea sensitivities) across all reading recommendations.
- 🎨 **Dynamic Cover Art & Video Trailers**: Creates custom book cover artwork and cinematic video trailers on demand, saved as session artifacts and public GCS links.
- 📍 **Local Bookstore & Library Finder**: Locates nearby physical bookstores and public libraries using live Google Maps geocoding and Places APIs.
- 📜 **Literary Companion & Excerpts**: Retrieves real public domain poetry and literary stanzas tailored to the user's reading mood.

---

## 🔮 Roadmap / Future Capabilities

- **Audiobook Voice Narration**: Multi-voice AI narration previews for book chapters (*planned, not yet implemented*).
- **Social Reading Circles**: Collaborative group reading list synchronizations (*planned, not yet implemented*).

---

## 🚀 Local Setup & Installation

### Prerequisites

- Python 3.11+
- Google Cloud Project with Vertex AI, Firestore, and Cloud Storage enabled
- Authenticated `gcloud` CLI credentials

### 1. Clone the Repository & Environment Setup

```bash
git clone <repository-url>
cd book-concierge
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the root directory:

```env
PROJECT_ID="your-gcp-project-id"
LOCATION="us-east1"
MODEL_NAME="gemini-2.0-flash"
AGENT_ENGINE_RESOURCE_NAME="projects/your-project-id/locations/us-east1/reasoningEngines/your-engine-id"
AGENT_DIRECTORY="app"
```

### 3. Run the Backend Agent Playground

```bash
python -m google.adk.cli playground app
```

### 4. Run the Web Frontend Server

```bash
cd frontend
pip install -r requirements.txt
python main.py
```

The web server will start and serve the chat interface locally on port `8080`.

---

## 📂 Repository Structure

```
book-concierge/
├── app/                      # Main ADK Agent definitions and tools
│   ├── agent.py              # Root orchestrator & sub-agents definition
│   ├── a2ui_utils.py         # A2UI schema manager & callbacks
│   ├── firestore_backend.py  # Firestore database integration
│   └── app_utils/            # Memory Bank and service helpers
├── frontend/                 # FastAPI proxy server and chat web UI
│   ├── main.py               # FastAPI proxy endpoint router
│   ├── static/index.html     # Glassmorphic chat interface
│   └── app/                  # Local agent fallback module
├── demo.gif                  # Inline looping demo recording
├── agents-cli-manifest.yaml  # ADK Agent manifest configuration
└── pyproject.toml            # Dependencies and build configuration
```
