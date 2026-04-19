import os
from googleapiclient.discovery import build
from google.oauth2 import service_account

# 1. Configuration
SERVICE_ACCOUNT_FILE = 'credentials.json' # The file he downloaded
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = 'your_spreadsheet_id_here'

def get_sheets_service():
    """Authenticates using the service account and returns the API client."""
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)
    return service

def append_to_sheet(new_rows):
    """
    Appends a list of lists to the bottom of the sheet.
    new_rows format: [['Company A', 'Python', 'CTO', 'url.com'], [...]]
    """
    service = get_sheets_service()

    # Define the range (Sheet1!A1 tells Google to start looking from the top-left)
    range_name = "Sheet1!A1"

    body = {
        'values': new_rows
    }

    try:
        result = service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
            valueInputOption="USER_ENTERED", # Parses dates/numbers correctly
            insertDataOption="INSERT_ROWS",  # Moves down to the first empty row
            body=body
        ).execute()

        print(f"✅ Success: {result.get('updates').get('updatedRows')} rows added to the bottom.")
    except Exception as e:
        print(f"❌ API Error: {e}")

# --- Example Usage ---
scraped_data = [
    ["Acme Corp", "Go, Docker", "Senior Backend Engineer", "https://stepstone.de/job123"],
    ["Global Tech", "React, TS", "Frontend Lead", "https://stepstone.de/job456"]
]

append_to_sheet(scraped_data)