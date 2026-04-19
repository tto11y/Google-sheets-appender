import os
from collections import defaultdict
from googleapiclient.discovery import build
from google.oauth2 import service_account

# 1. Configuration
SERVICE_ACCOUNT_FILE = 'credentials.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# 2. The Master Mapping (Company Name : Spreadsheet ID)
COMPANY_TO_SHEET_MAP = {
    "Acme Corp": "1abc_ID_from_URL_123",
    "Global Tech": "2xyz_ID_from_URL_456",
    "Cyberdyne Systems": "3pqr_ID_from_URL_789",
}

def get_sheets_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('sheets', 'v4', credentials=creds)

def distribute_contacts_to_sheets(all_contacts):
    """
    all_contacts: A list of dicts, e.g.
    [{'company': 'Acme Corp', 'name': 'John Doe', 'email': 'john@acme.com'}, ...]
    """
    service = get_sheets_service()

    # Step 1: Group contacts by company to minimize API calls
    buckets = defaultdict(list)
    for contact in all_contacts:
        company = contact.get('company')
        # We convert the dict to a simple list for the Sheets API
        row = [contact.get('name'), contact.get('email'), contact.get('role'), contact.get('phone')]
        buckets[company].append(row)

    # Step 2: Iterate through the buckets and write to the specific IDs
    for company, rows in buckets.items():
        spreadsheet_id = COMPANY_TO_SHEET_MAP.get(company)

        if not spreadsheet_id:
            print(f"⚠️ Warning: No Spreadsheet ID found for '{company}'. Skipping.")
            continue

        try:
            service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range="Sheet1!A1",
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body={'values': rows}
            ).execute()
            print(f"✅ Appended {len(rows)} contacts to {company}'s sheet.")
        except Exception as e:
            print(f"❌ Error writing to {company}: {e}")

# --- Example of his enriched lead list ---
lead_list = [
    {'company': 'Acme Corp', 'name': 'Sarah Connor', 'email': 's.connor@acme.com', 'role': 'CTO', 'phone': '+49...'},
    {'company': 'Global Tech', 'name': 'Thomas Anderson', 'email': 'neo@gt.com', 'role': 'Lead Dev', 'phone': '+49...'},
    {'company': 'Acme Corp', 'name': 'Miles Dyson', 'email': 'm.dyson@acme.com', 'role': 'Engineering Manager', 'phone': '+49...'},
]

distribute_contacts_to_sheets(lead_list)