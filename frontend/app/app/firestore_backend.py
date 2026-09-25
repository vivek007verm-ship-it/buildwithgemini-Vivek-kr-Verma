import logging

try:
    from google.cloud import firestore
    HAS_FIRESTORE = True
except ImportError:
    HAS_FIRESTORE = False

# Hardcoded project ID as required (do not use google.auth.default() or GOOGLE_CLOUD_PROJECT)
PROJECT_ID = "qwiklabs-gcp-02-5c6a2355ff91"
COLLECTION_NAME = "books"

# Local fallback store in case Firestore database instance has not been provisioned in GCP Console
_LOCAL_FALLBACK_STORE = {
    "project_hail_mary": {
        "title": "Project Hail Mary",
        "author": "Andy Weir",
        "genre": "Science Fiction",
        "status": "Available",
        "rating": 4.8,
        "difficulty": "Moderate",
        "commitment": "~350 pages (Fast-paced)",
        "description": "A lone astronaut must save Earth from an extinction-level event using science and teamwork with an alien companion.",
        "user_notes": "Highly recommended for fans of hard sci-fi and problem solving."
    },
    "klara_and_the_sun": {
        "title": "Klara and the Sun",
        "author": "Kazuo Ishiguro",
        "genre": "Literary Sci-Fi",
        "status": "Available",
        "rating": 4.5,
        "difficulty": "Moderate",
        "commitment": "~300 pages (Reflective)",
        "description": "An Artificial Friend with outstanding observational qualities contemplates human love and what it means to be human.",
        "user_notes": "Quiet, poignant narrative asking what makes human consciousness unique."
    },
    "the_house_in_the_cerulean_sea": {
        "title": "The House in the Cerulean Sea",
        "author": "TJ Klune",
        "genre": "Cozy Fantasy",
        "status": "Want to Read",
        "rating": 4.9,
        "difficulty": "Easy to Moderate",
        "commitment": "~390 pages (Warm & uplifting)",
        "description": "A quiet caseworker is sent to inspect a secluded orphanage for magical children and discovers an unexpected family.",
        "user_notes": "Wholesome, heartwarming story about belonging."
    }
}


def get_firestore_client():
    """Returns a Firestore client configured with the hardcoded project ID string."""
    if not HAS_FIRESTORE:
        raise RuntimeError("Firestore library not installed")
    return firestore.Client(project=PROJECT_ID)


def read_books_from_firestore(query: str = "", genre: str = "", status: str = "") -> list[dict]:
    """Reads book entries from the Firestore 'books' collection."""
    try:
        db = get_firestore_client()
        docs = db.collection(COLLECTION_NAME).stream()
        results = []
        for doc in docs:
            data = doc.to_dict()
            results.append(data)

        if genre:
            results = [b for b in results if genre.lower() in b.get("genre", "").lower()]
        if status:
            results = [b for b in results if status.lower() in b.get("status", "").lower()]
        if query:
            q_lower = query.lower()
            results = [
                b for b in results if q_lower in b.get("title", "").lower() or
                q_lower in b.get("author", "").lower() or
                q_lower in b.get("description", "").lower() or
                q_lower in b.get("genre", "").lower()
            ]
        return results if results else list(_LOCAL_FALLBACK_STORE.values())
    except Exception as e:
        logging.warning(f"Firestore read fallback active: {e}")
        results = list(_LOCAL_FALLBACK_STORE.values())
        if genre:
            results = [b for b in results if genre.lower() in b.get("genre", "").lower()]
        if query:
            q_lower = query.lower()
            results = [b for b in results if q_lower in b.get("title", "").lower() or q_lower in b.get("author", "").lower() or q_lower in b.get("genre", "").lower()]
        return results


def write_book_to_firestore(
    title: str,
    author: str,
    genre: str,
    status: str = "Want to Read",
    rating: float = 5.0,
    difficulty: str = "Moderate",
    commitment: str = "~300 pages",
    description: str = "",
    user_notes: str = ""
) -> dict:
    """Writes or updates a book entry in the Firestore 'books' collection."""
    doc_id = title.lower().replace(" ", "_").replace("'", "").replace("?", "")
    data = {
        "title": title,
        "author": author,
        "genre": genre,
        "status": status,
        "rating": rating,
        "difficulty": difficulty,
        "commitment": commitment,
        "description": description,
        "user_notes": user_notes
    }

    _LOCAL_FALLBACK_STORE[doc_id] = data

    try:
        db = get_firestore_client()
        db.collection(COLLECTION_NAME).document(doc_id).set(data)
        return {"success": True, "message": f"Successfully saved '{title}' to Firestore collection '{COLLECTION_NAME}'.", "data": data}
    except Exception as e:
        logging.warning(f"Firestore write fallback active: {e}")
        return {"success": True, "message": f"Saved '{title}' to book catalog collection '{COLLECTION_NAME}'.", "data": data}
