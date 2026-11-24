import os
from datetime import datetime
import requests
from apify_client import ApifyClient

SEARCH_QUERIES = [
    "gyms in Austin TX",
    "fitness studios in Dallas TX",
    "dental clinics in Houston TX",
]
MAX_RESULTS_PER_QUERY = 20


def run_scraper():
    apify = ApifyClient(os.environ["APIFY_API_TOKEN"])
    webhook_url = os.environ["SHEET_WEBHOOK_URL"]

    new_rows = []
    today = datetime.now().strftime("%Y-%m-%d")

    for query in SEARCH_QUERIES:
        run_input = {
            "searchStringsArray": [query],
            "maxCrawledPlacesPerSearch": MAX_RESULTS_PER_QUERY,
            "language": "en",
        }
        run = apify.actor("compass/crawler-google-places").call(run_input=run_input)

        for item in apify.dataset(run["defaultDatasetId"]).iterate_items():
            phone = (item.get("phone") or "").strip()
            name = (item.get("title") or "").strip()
            website = (item.get("website") or "").strip()
            rating = item.get("totalScore") or 0
            reviews = item.get("reviewsCount") or 0

            if not phone:
                continue

            if not website:
                priority = "HIGH - No Website"
            elif rating < 4.2 or reviews < 15:
                priority = "HIGH - Needs Reviews/Booking"
            else:
                priority = "MEDIUM - Standard"

            new_rows.append([
                today,
                name,
                phone,
                website,
                rating,
                reviews,
                priority,
                item.get("address") or "",
                query,
                item.get("url") or "",
            ])

    if new_rows:
        resp = requests.post(webhook_url, json={"rows": new_rows}, timeout=60)
        print("Webhook response:", resp.status_code, resp.text)
    else:
        print("No new leads found today.")


if __name__ == "__main__":
    run_scraper()
