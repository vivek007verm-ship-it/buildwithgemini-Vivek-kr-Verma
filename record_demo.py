import os
import sys
import time
import asyncio
from playwright.async_api import async_playwright
from google.cloud import storage

async def record_demo():
    video_dir = "/tmp/demo_video"
    os.makedirs(video_dir, exist_ok=True)

    async with async_playwright() as p:
        # Launch browser with video recording enabled
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            record_video_dir=video_dir,
            record_video_size={"width": 1280, "height": 800}
        )

        page = await context.new_page()
        print("Navigating to live Book Concierge frontend...")
        await page.goto("https://book-concierge-frontend-qgmhq3c5ta-ue.a.run.app", wait_until="networkidle")
        await asyncio.sleep(2)

        input_selector = "#userInput"
        send_selector = "#sendBtn"

        # 1. First prompt: App core capability (recommendation request)
        print("Sending prompt 1...")
        prompt1 = "I am looking for a dark noir mystery novel set in a rainy 1940s city. Recommend something atmospheric."
        await page.fill(input_selector, prompt1)
        await page.click(send_selector)

        # Wait for agent streaming response to finish
        print("Waiting for prompt 1 response...")
        await asyncio.sleep(14)

        # 2. Second richer prompt: Showing off tool call, database lookup, cover art, and video trailer
        print("Sending prompt 2...")
        prompt2 = "Can you search Firestore for mystery books, fetch external details, and generate a cover illustration and short video trailer for The Maltese Falcon?"
        await page.fill(input_selector, prompt2)
        await page.click(send_selector)

        # Wait for prompt 2 tool execution & streaming response
        print("Waiting for prompt 2 response and tool calls...")
        await asyncio.sleep(20)

        print("Finished demo recording session. Closing browser...")
        await page.close()
        await context.close()
        await browser.close()

    # Find the recorded video file
    video_files = [os.path.join(video_dir, f) for f in os.listdir(video_dir) if f.endswith(".webm") or f.endswith(".mp4")]
    if not video_files:
        print("Error: No video file found in", video_dir)
        return

    recorded_path = video_files[0]
    print(f"Recorded video saved to: {recorded_path}")

    # Upload video to public Cloud Storage bucket
    bucket_name = "book-concierge-qwiklabs-gcp-02-5c6a2355ff91"
    gcs_filename = "book_concierge_demo.webm"
    print(f"Uploading {recorded_path} to gs://{bucket_name}/{gcs_filename}...")

    storage_client = storage.Client(project="qwiklabs-gcp-02-5c6a2355ff91")
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(gcs_filename)
    blob.upload_from_filename(recorded_path, content_type="video/webm")

    public_url = f"https://storage.googleapis.com/{bucket_name}/{gcs_filename}"
    print("\n" + "="*60)
    print(f"DEMO VIDEO PUBLIC URL: {public_url}")
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(record_demo())
