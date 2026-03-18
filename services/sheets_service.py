import os
import time
import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

class SheetsService:
    def __init__(self):
        creds_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH")
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        if not creds_path or not sheet_id:
            raise ValueError("GOOGLE_SHEETS_CREDENTIALS_PATH and GOOGLE_SHEET_ID must be set")
        creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(sheet_id)
        self.worksheet = spreadsheet.worksheet("Successful Reviews")
        self.failed_worksheet = spreadsheet.worksheet("Failed Reviews")

    def log_review(self, row: dict) -> None:
        data = [
            row["date"],
            row["url"],
            row["author"],
            row["total_comments"],
            row["files_reviewed"],
            row["high"],
            row["medium"],
            row["low"],
        ]
        for attempt in range(3):
            try:
                self.worksheet.append_row(data, value_input_option="USER_ENTERED")
                return
            except gspread.exceptions.APIError as e:
                if attempt == 2:
                    raise
                print(f"Sheets API error (attempt {attempt + 1}/3): {e}, retrying...")
                time.sleep(2 ** attempt)

    def log_failure(self, row: dict) -> None:
        data = [
            row["date"],
            row["url"],
            row["author"],
            row["error"],
        ]
        for attempt in range(3):
            try:
                self.failed_worksheet.append_row(data, value_input_option="USER_ENTERED")
                return
            except gspread.exceptions.APIError as e:
                if attempt == 2:
                    raise
                print(f"Sheets API error (attempt {attempt + 1}/3): {e}, retrying...")
                time.sleep(2 ** attempt)
