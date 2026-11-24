import os
from datetime import datetime
import requests
from apify_client import ApifyClient

DAILY_NICHE_POOL = [
    ["restaurants in Austin TX", "gyms in Dallas TX", "car dealerships in Houston TX"],
    ["beauty salons in Miami FL", "dental clinics in Tampa FL", "hotels in Orlando FL"],
    ["auto repair shops in Phoenix AZ", "real estate agencies in Scottsdale AZ", "pet grooming in Mesa AZ"],
    ["law firms in Atlanta GA", "coffee shops in Charlotte NC", "event planners in Raleigh NC"],
    ["chiropractors in Denver CO", "moving companies in Nashville TN", "spas in Las Vegas NV"],
    ["home builders in Chicago IL", "accounting firms in Columbus OH", "cleaning services in Indianapolis IN"],
    ["fitness studios in San Diego CA", "veterinary clinics in Sacramento CA", "clothing boutiques in San Jose CA"],
    ["plumbers in Seattle WA", "roofers in Denver CO", "marketing agencies in Miami FL"],
    ["insurance agencies in Dallas TX", "florists in Austin TX", "bakeries in Chicago IL"],
]

MAX_RESULTS_PER_QUERY = 25


def run_scraper():
    apify = ApifyClient(os.environ["APIFY_API_TOKEN"])
    webhook_url = os.environ["SHEET_WEBHOOK_URL"]

    day_index = datetime.now().timetuple().tm_yday % len(DAILY_NICHE_POOL)
    todays_queries = DAILY_NICHE_POOL[day_index]

    new_rows = []
    today = datetime.now().strftime("%d-%m-%Y")

    for query in todays_queries:
        run_input = {
            "searchStringsArray": [query],
            "maxCrawledPlacesPerSearch": MAX_RESULTS_PER_QUERY,
            "language": "en",
            "scrapeContacts": True,
        }
        run = apify.actor("compass/crawler-google-places").call(run_input=run_input)
        dataset_id = run.default_dataset_id if hasattr(run, "default_dataset_id") else run["defaultDatasetId"]

        for item in apify.dataset(dataset_id).iterate_items():
            phone = (item.get("phone") or "").strip()
            name = (item.get("title") or "").strip()
            website = (item.get("website") or "").strip()
            rating = item.get("totalScore") or 0
            reviews = item.get("reviewsCount") or 0

            emails_list = item.get("emails") or []
            email = ", ".join(emails_list) if isinstance(emails_list, list) else str(emails_list)

            if not phone:
                continue

            if not website:
                priority = "HIGH - No Website"
            elif rating < 4.3 or reviews < 25:
                priority = "HIGH - Needs Reviews/Booking"
            else:
                priority = "MEDIUM - Standard"

            new_rows.append([
                today,
                name,
                phone,
                email,
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
