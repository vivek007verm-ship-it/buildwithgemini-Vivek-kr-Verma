import time
import logging
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-02-5c6a2355ff91"

SEEDED_BOOKS = [
    {
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
    {
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
    {
        "title": "The House in the Cerulean Sea",
        "author": "TJ Klune",
        "genre": "Cozy Fantasy",
        "status": "Want to Read",
        "rating": 4.9,
        "difficulty": "Easy to Moderate",
        "commitment": "~390 pages (Warm & uplifting)",
        "description": "A quiet caseworker is sent to inspect a secluded orphanage for magical children and discovers an unexpected family.",
        "user_notes": "Wholesome, heartwarming story about belonging."
    },
    {
        "title": "Piranesi",
        "author": "Susanna Clarke",
        "genre": "Fantasy / Mystery",
        "status": "Finished",
        "rating": 4.7,
        "difficulty": "Moderate",
        "commitment": "~240 pages (Immersive)",
        "description": "Piranesi lives in a labyrinthine House containing infinite halls and tides, recording its wonders until evidence of another person emerges.",
        "user_notes": "Unique worldbuilding and atmospheric mystery."
    },
    {
        "title": "Atomic Habits",
        "author": "James Clear",
        "genre": "Non-Fiction",
        "status": "Available",
        "rating": 4.8,
        "difficulty": "Easy",
        "commitment": "~320 pages (Actionable)",
        "description": "A practical framework for building good habits and breaking bad ones using small, incremental daily changes.",
        "user_notes": "Actionable insights for habit formation."
    }
]


def seed_database():
    print(f"Connecting to Firestore with hardcoded project ID: {PROJECT_ID}...")
    db = firestore.Client(project=PROJECT_ID)
    collection_ref = db.collection("books")

    for book in SEEDED_BOOKS:
        doc_id = book["title"].lower().replace(" ", "_").replace("'", "").replace("?", "")
        doc_ref = collection_ref.document(doc_id)
        
        # Retry loop for IAM cache propagation
        for attempt in range(5):
            try:
                doc_ref.set(book)
                print(f"Successfully seeded book: '{book['title']}' (ID: {doc_id})")
                break
            except Exception as e:
                if attempt == 4:
                    print(f"Failed to seed '{book['title']}': {e}")
                time.sleep(2)

    print("Firestore seeding complete!")


if __name__ == "__main__":
    seed_database()
