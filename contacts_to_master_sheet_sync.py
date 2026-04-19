import io
import pandas as pd
from googleapiclient.discovery import build
from google.oauth2 import service_account
from collections import defaultdict

# Configuration
SERVICE_ACCOUNT_FILE = 'credentials.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = 'YOUR-SPREADSHEET-ID'

# Global references for dict keys to prevent mismatches
CSV_COMPANY_KEY = 'company_domain'
CSV_DATA_KEY = 'data'

# Documentation Template
# This will be added to the top of EVERY new company tab created
TEMPLATE_HEADER = [
    ["Account"],
    [""],
    ["Goal"],
    [""],
    ["Strategy"],
    [""],
    ["Initiatives"],
    [""],
    [""],
    ["Problem Hypothesis (Problem & Business Implication)"],
    [""],
    ["Why us? (What is it we do uniquely different that solves this problem)"],
    [""],
    ["Social Proof (Where have we done it before)"],
    [""],
    ["Decision Maker / Economic Buyer", "Notes (What do we know specifically about that person)"],
    ["", ""],
    [""],
    ["Vacancy:", ""],
    [""],
    ["First Name", "Last Name", "Title", "Location", "LinkedIn", "Email", "Phone", "Use Case", "Contacted?", "Notes"],
    ["-"],
]


def sync_to_sheets(csv_raw_data, company_key, data_key):
    service = get_sheets_service()
    existing_tabs = get_existing_tab_names(service)

    buckets = process_csv(csv_raw_data, company_key, data_key)

    for company_domain, rows in buckets.items():
        # Sanitize company name for Google Sheet tab naming rules
        if len(company_domain) > 30:
            print(
                f"company domain {company_domain} has more than 30 characters; we need to shrink it to comply with Google Sheet tab naming rules")
        tab_name = company_domain[:30].replace("'", "").replace("*", "")
        print(f"tab name: {tab_name} (=sanitized company domain)")

        if tab_name not in existing_tabs:
            try:
                create_tab_with_template(service, tab_name)
                existing_tabs.append(tab_name)
            except Exception as e:
                print(f"Error creating tab for {tab_name}: {e}")
                continue

        # Append data starting from the bottom of the template
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f"'{tab_name}'!A1:J21",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={'values': rows},
        ).execute()
        print(f"✅ Successfully routed {len(rows)} contacts to tab: {tab_name}")


def get_sheets_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('sheets', 'v4', credentials=creds)


def get_existing_tab_names(service):
    """Returns a list of all tab names currently in the spreadsheet."""
    spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    return [sheet['properties']['title'] for sheet in spreadsheet.get('sheets', [])]


def process_csv(csv_raw_data, company_key, data_key):
    leads = process_clay_csv(csv_raw_data, company_key, data_key)

    # Group by company
    buckets = defaultdict(list)
    for lead in leads:
        if lead[company_key]:  # Skip rows with no company name
            buckets[lead[company_key]].append(lead[data_key])

    return buckets


def process_clay_csv(csv_content, company_key, data_key):
    """
    Reads the CSV (file path or string) and extracts only the relevant columns.
    """
    # Use io.StringIO if passing a raw string, otherwise just pd.read_csv(file_path)
    df = pd.read_csv(io.StringIO(csv_content))

    # these column names correspond to the relevant columns in the CSV exported from Clay
    relevant_cols = [
        "Company Domain",
        "First Name",
        "Last Name",
        "Job Title",
        "Location",
        "LinkedIn Profile",
        "Formula",
        "Formula (2)"
    ]

    # Clean the dataframe to only what we need
    df = df[relevant_cols].fillna("")  # Replace NaNs with empty strings

    lead_list = []
    for _, row in df.iterrows():
        lead_list.append({
            company_key: str(row[relevant_cols[0]]).strip(),
            data_key: [
                row[relevant_cols[1]],
                row[relevant_cols[2]],
                row[relevant_cols[3]],
                row[relevant_cols[4]],
                row[relevant_cols[5]],
                row[relevant_cols[6]],  # Usually the Email from Clay waterfall
                row[relevant_cols[7]],  # Usually the Phone from Clay waterfall
                "",  # Placeholder for 'Use Case'
                "",  # Placeholder for 'Contacted?'
                "",  # Placeholder for 'Notes'
            ]
        })
    return lead_list


def create_tab_with_template(service, company_name):
    batch_update_request = {'requests': [{'addSheet': {'properties': {'title': company_name}}}]}
    response = service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body=batch_update_request).execute()
    sheet_id = response['replies'][0]['addSheet']['properties']['sheetId']

    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"'{company_name}'!A1",
        valueInputOption="USER_ENTERED",
        body={'values': TEMPLATE_HEADER}
    ).execute()

    # Apply Formatting (Batch Update)
    # Color: Dark Blue 3 (Hex #083763) -> RGB normalized to 0-1
    dark_blue_3 = hex_to_sheets_rgb("#083763")
    white_text = hex_to_sheets_rgb("#FFFFFF")

    rows_to_be_styled = [0, 2, 4, 6, 9, 11, 13, 15, 20]

    rows_to_be_merged = rows_to_be_styled.copy()
    rows_to_be_merged.extend([1, 3, 5, 7, 10, 12, 14, 16])
    rows_to_be_merged.pop(rows_to_be_merged.index(20))  # header of contacts must not be merged

    format_requests = generate_horizontal_merge_requests(sheet_id, rows_to_be_merged)
    tmp = generate_style_requests(sheet_id, rows_to_be_styled, white_text, dark_blue_3)

    format_requests.extend(tmp)

    service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={"requests": format_requests}).execute()
    print(f"🎨 Created and formatted tab: {company_name}")


def hex_to_sheets_rgb(hex_color):
    """
    Converts a hex string (e.g., '#083763') to a Google Sheets RGB object.
    """
    hex_color = hex_color.lstrip('#')
    # Convert hex to decimal (0-255) and normalize to 0.0-1.0
    return {
        "red": int(hex_color[0:2], 16) / 255.0,
        "green": int(hex_color[2:4], 16) / 255.0,
        "blue": int(hex_color[4:6], 16) / 255.0
    }


def generate_horizontal_merge_requests(sheet_id, indexes, start_col=0, end_col=10):
    """
    Produces a list of mergeCells JSON objects for each row in the specified range.

    Args:
        sheet_id (int): The ID of the specific tab.
        indexes (list): The indexes of the rows that should be merged (0-indexed).
        start_col (int): Starting column (default 0/A).
        end_col (int): Ending column (default 10/J).
    """
    requests = []

    # We iterate through each row index in the range
    for row_index in indexes:
        requests.append({
            "mergeCells": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": row_index,
                    "endRowIndex": row_index + 1,  # +1 because endRowIndex is exclusive
                    "startColumnIndex": start_col,
                    "endColumnIndex": end_col
                },
                "mergeType": "MERGE_ALL"
            }
        })

    return requests


def generate_style_requests(sheet_id, indexes, foreground_color, background_color):
    """
    Produces a list of mergeCells JSON objects for each row in the specified range.

    Args:
        sheet_id (int): The ID of the specific tab.
        indexes (list): The indexes of the rows that should be merged (0-indexed).
        background_color: The color of the background (RGB)
        foreground_color: The color of the foreground (RGB)
    """
    requests = []

    # We iterate through each row index in the range
    for row_index in indexes:
        requests.append(
            {
                "repeatCell": {
                    "range": {"sheetId": sheet_id, "startRowIndex": row_index, "endRowIndex": row_index + 1},
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": background_color,
                            "textFormat": {"foregroundColor": foreground_color, "fontSize": 11, "bold": True},
                            "horizontalAlignment": "LEFT"
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
                }
            }
        )

    return requests


# --- EXECUTION ---
# You can just paste the CSV content here:
# RAW_CSV_INPUT = """Paste CSV Content Here"""

# Or read from a file:
with open('clay_export.csv', 'r', encoding='utf-8') as f:
    RAW_CSV_INPUT = f.read()

if __name__ == "__main__":
    sync_to_sheets(RAW_CSV_INPUT, CSV_COMPANY_KEY, CSV_DATA_KEY)
