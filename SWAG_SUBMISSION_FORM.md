# Build with Gemini — Project & Swag Submission Form

---

### 👤 Participant Information

| Field | Details |
| :--- | :--- |
| **Participant Name** | Vivek kr Verma |
| **Project Repository Name** | `buildwithgemini-Vivek-kr-Verma` |
| **Track / Event** | Build with Gemini — AI Agent Track |
| **Submission Date** | September 25, 2026 |

---

### 🤖 Project Overview

| Field | Details |
| :--- | :--- |
| **Agent / App Name** | **Book Concierge** — AI Personal Librarian |
| **Tagline** | An intelligent multi-agent assistant for personalized book discovery, preference memory, cover art, and cinematic video trailers. |
| **Primary Framework** | Google Agent Development Kit (ADK) |
| **Orchestrator Architecture** | Multi-agent hierarchy (`reader_agent`, `discovery_agent`, `memory_agent`, `recommendation_agent`, `companion_agent`, `journey_agent`) |

---

### ☁️ Google Cloud Services & Technologies Integrated

1. **Vertex AI Reasoning Engine** (`us-east1`)
   - Deployed reasoning engine hosting root multi-agent orchestrator.
2. **Vertex AI Memory Bank**
   - Persistent user reading preferences, mood, and health/allergy constraints tracking via `preload_memory` and `load_memory`.
3. **Google Cloud Storage (GCS)**
   - Public storage bucket (`book-concierge-qwiklabs-gcp-02-5c6a2355ff91`) storing generated cover art and video trailers.
4. **Google Cloud Firestore**
   - Document store for catalog indexing, book metadata, and reading history queries.
5. **Google GenAI / Omni Models**
   - **Cover Art Generation**: Dynamic 600x900 book illustration canvas and image generation.
   - **Video Trailers**: Google Omni Model (`gemini-omni-flash-preview`) in the `global` region generating cinematic MP4 book trailers.
6. **Google Maps Places (New) API**
   - Geocoding and location-based search for nearby physical bookstores and libraries.
7. **A2UI Declarative UI Protocol**
   - `A2uiSchemaManager` and `after_model_callback` for rich UI components.

---

### 🎥 Demo Assets

- **Repository README**: Contains embedded looping GIF (`demo.gif`)
- **Public Video Trailer & Demo Link**: [https://storage.googleapis.com/book-concierge-qwiklabs-gcp-02-5c6a2355ff91/book_concierge_lofi_demo.mp4](https://storage.googleapis.com/book-concierge-qwiklabs-gcp-02-5c6a2355ff91/book_concierge_lofi_demo.mp4)
- **Inline GIF Recording**: [`demo.gif`](demo.gif)

---

### 📌 Setup & Verification

```bash
# Clone & install
git clone https://github.com/<your-username>/buildwithgemini-Vivek-kr-Verma.git
cd buildwithgemini-Vivek-kr-Verma
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run Web UI
cd frontend
python main.py
```
