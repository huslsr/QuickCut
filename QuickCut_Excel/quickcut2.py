import requests
import json
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

# ------------------ API KEYS ------------------
API_KEY = "f6c24c1b018891bc9075c60890860323"
QUERY = "cricket"
LANG = "en"
MAX_RESULTS = 1

GNEWS_API = f"https://gnews.io/api/v4/search?q={QUERY}&lang={LANG}&max={MAX_RESULTS}&apikey={API_KEY}"

GEN_AI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key="
GEN_AI_API_KEY = "AIzaSyCOKPBzAeqOocXuiiH44NGBIGLX-IrnlrY"

# ------------------ Google Sheets Setup ------------------
SHEET_ID = "1_d1OWlqcfxDRnP7aIjv8ugDZfGE2bpqlfgkD4TopAww"   # your sheet ID
SHEET_NAME = "Sheet1"
CREDENTIALS_FILE = "service_account.json"

HEADERS = ["idx","id", "Title", "URL", "Image", "PublishedAt", "Summary"]

def main():
    # -------- Fetch news from GNews --------
    resp = requests.get(GNEWS_API)
    data = resp.json()
    articles = data.get("articles", [])

    results = []

    for idx, article in enumerate(articles, start=1):
        id = article.get("id", "")
        title = article.get("title", "")
        description = article.get("description", "")
        content = article.get("content", "")
        image = article.get("image", "")
        url = article.get("url", "")
        published_at = article.get("publishedAt", "")

        article_text = f"Title: {title}\nDescription: {description}\nContent: {content}"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": "You are a journalist. Summarize the following article into a concise 3-minute read. Do NOT include the title; provide content only suitable for copy-paste."},
                        {"text": article_text}
                    ]
                }
            ]
        }

        gen_resp = requests.post(
            GEN_AI_URL + GEN_AI_API_KEY,
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload)
        )

        if gen_resp.status_code == 200:
            gen_data = gen_resp.json()
            summary = gen_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        else:
            summary = f"Error: {gen_resp.text}"

        results.append([idx,id, title, url, image, published_at, summary])

    # -------- Push to Google Sheet --------
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

    # If sheet is empty → add headers first
    if len(sheet.get_all_values()) == 0:
        sheet.insert_row(HEADERS, 1)  # <-- FIXED: use HEADERS not df

    # ✅ Ensure headers exist
    first_row = sheet.row_values(1)
    if first_row != HEADERS:
        sheet.insert_row(HEADERS, 1)

# Fetch existing IDs from the sheet
    existing_records = sheet.get_all_records()
    existing_ids = {record["id"] for record in existing_records}  # set of already stored ids

    # Append rows at bottom only if ID not present
    for row in results:
        row_id = row[1]  # index 1 corresponds to "id" column
        if row_id not in existing_ids:
            sheet.append_row(row)
            existing_ids.add(row_id)  # update set to avoid duplicates in same run

    print("✅ Data updated in Google Sheet with headers")

    # -------- Download latest sheet as Excel --------
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    df.to_excel("news_results.xlsx", index=False)
    print("📥 Downloaded latest data to news_results.xlsx")

if __name__ == "__main__":
    main()
