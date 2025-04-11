from fastapi import FastAPI,Body, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pytz
import json
import asyncio
from collections import deque
import uvicorn
import re
from autocaptchavip import PuzzleCaptchaSolver
app = FastAPI(title="Ticket Tracking API")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
CREDENTIALS_FILE = 'service_account.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = "1ExRHONdCvGq--lZggVEQFGHhhkMYtCuZiOiOisbWTj0"
SHEET_NAME = 'huy1'
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# Global variables
ticket_queue = deque()
vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')
sheets_service = None

### Helper Functions ###
def init_google_sheets():
    global sheets_service
    try:
        if sheets_service is None:
            with open(CREDENTIALS_FILE, 'r') as file:
                creds_info = json.load(file)
            creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
            sheets_service = build('sheets', 'v4', credentials=creds)
        return sheets_service
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Google Sheets connection error: {str(e)}")

def ensure_headers_and_format(service):
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range=f"{SHEET_NAME}!A1:D1"
        ).execute()
        headers = result.get('values', [])
        expected_headers = ["ID Profile", "Ticket", "Trạng thái", "Cập nhật cuối"]

        if not headers or headers[0] != expected_headers:
            service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{SHEET_NAME}!A1:D1",
                valueInputOption="USER_ENTERED",
                body={"values": [expected_headers]}
            ).execute()

        service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={
                "requests": [{
                    "repeatCell": {
                        "range": {
                            "sheetId": 0,
                            "startColumnIndex": 3,
                            "endColumnIndex": 4
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "numberFormat": {
                                    "type": "DATE_TIME",
                                    "pattern": "yyyy-mm-dd hh:mm:ss"
                                }
                            }
                        },
                        "fields": "userEnteredFormat.numberFormat"
                    }
                }]
            }
        ).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Header configuration error: {str(e)}")

def parse_timestamp(timestamp_str):
    try:
        return vietnam_tz.localize(datetime.strptime(timestamp_str, TIME_FORMAT))
    except ValueError:
        try:
            days = float(timestamp_str.replace(',', '.'))
            base_date = datetime(1899, 12, 30, tzinfo=vietnam_tz)
            return base_date + timedelta(days=days)
        except ValueError:
            raise ValueError(f"Invalid timestamp format: {timestamp_str}")

def check_existing_tickets(service):
    global ticket_queue
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, 
            range=f"{SHEET_NAME}!A2:D",
            majorDimension="ROWS"
        ).execute()
        
        rows = result.get('values', [])
        now = datetime.now(vietnam_tz)
        expired_rows = []

        for i, row in enumerate(rows, start=2):
            if len(row) < 4:
                continue
            
            try:
                ticket_time = parse_timestamp(row[3])
                expiry_time = ticket_time + timedelta(minutes=5)
                
                if now >= expiry_time:
                    expired_rows.append(i)
                else:
                    ticket_queue.append((i, expiry_time))
            except ValueError as e:
                print(f"Timestamp parse error at row {i}: {e}")
                continue

        for row in sorted(expired_rows, reverse=True):
            id_to_keep = rows[row-2][0] if len(rows[row-2]) > 0 else ""
            values = [[id_to_keep, "", "", ""]]
            
            service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{SHEET_NAME}!A{row}:D{row}",
                valueInputOption="USER_ENTERED",
                body={"values": values}
            ).execute()
            
            print(f"Cleared expired ticket at row {row}, kept ID: {id_to_keep}")

    except Exception as e:
        print(f"Error checking existing tickets: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ticket check error: {str(e)}")

async def cleanup_expired_tickets():
    global ticket_queue
    while True:
        try:
            service = init_google_sheets()
            now = datetime.now(vietnam_tz)
            expired_rows = []

            while ticket_queue:
                row, expiry = ticket_queue[0]
                if now >= expiry:
                    expired_rows.append(row)
                    ticket_queue.popleft()
                else:
                    break

            if expired_rows:
                for row in sorted(expired_rows, reverse=True):
                    result = service.spreadsheets().values().get(
                        spreadsheetId=SPREADSHEET_ID,
                        range=f"{SHEET_NAME}!A{row}:A{row}"
                    ).execute()
                    id_to_keep = result.get('values', [[""]])[0][0]
                    
                    service.spreadsheets().values().update(
                        spreadsheetId=SPREADSHEET_ID,
                        range=f"{SHEET_NAME}!A{row}:D{row}",
                        valueInputOption="USER_ENTERED",
                        body={"values": [[id_to_keep, "", "", ""]]}
                    ).execute()
                    
                    print(f"Auto-cleared expired ticket at row {row}")

            await asyncio.sleep(10)
        except Exception as e:
            print(f"Cleanup error: {str(e)}")
            await asyncio.sleep(10)
# giải captcha
@app.post("/api/verify-captcha")
async def verify_captcha(body: dict = Body(...)):
    try:
        solver = PuzzleCaptchaSolver(
            gap_image_url=body["gap_image_url"],
            bg_image_url=body["bg_image_url"],
            output_image_path=body.get("output_image_path", "result/result.png"),
            gap_image_folder=body.get("gap_image_folder", "gap_image"),
            json_path=body.get("json_path", "captcha.json")
        )
        result = solver.discern()
        
        if result["position"] is None:
            raise HTTPException(400, "Failed to solve captcha")
            
        return {
            "status": True,
            "message": "Success",
            "result": {k: result[k] for k in ["position", "best_confidence", "best_gap_image",
                                            "gap_url", "result_image", "nearest_puzzle_left",
                                            "nearest_slider_left"]}
        }
    except FileNotFoundError as e:
        raise HTTPException(404, f"File not found: {e}")
    except KeyError as e:
        raise HTTPException(400, f"Missing required field: {e}")
    except Exception as e:
        raise HTTPException(500, f"Error")
### API Endpoints ###
@app.post("/api/add-ticket")
async def add_ticket(ticket: str = Form(...)):
    global ticket_queue
    try:
        service = init_google_sheets()
        ensure_headers_and_format(service)
        
        now = datetime.now(vietnam_tz)
        expiry = now + timedelta(minutes=5)
        timestamp = now.strftime(TIME_FORMAT)
        
        # Lấy dữ liệu hiện tại từ sheet (chỉ cột B trở đi)
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!B2:D",
            majorDimension="ROWS"
        ).execute()
        
        rows = result.get('values', [])
        
        # Tìm ô trống đầu tiên trong cột B
        target_row = None
        for i, row in enumerate(rows, start=2):
            if len(row) == 0 or not row[0].strip():  # Nếu ô B trống
                target_row = i
                break
        
        # Nếu không tìm thấy ô trống trong dữ liệu hiện có, thêm vào hàng tiếp theo
        if target_row is None:
            target_row = len(rows) + 2
        
        # Ghi ticket mới vào ô B của hàng target_row
        values = [[ticket, "Mới", timestamp]]
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!B{target_row}:D{target_row}",  # Chỉ ghi từ B đến D
            valueInputOption="USER_ENTERED",
            body={"values": values}
        ).execute()
        
        # Cập nhật ticket_queue
        ticket_queue.append((target_row, expiry))
        
        return {
            "status": True,
            "message": f"Đã thêm ticket vào ô B{target_row}"
        }
            
    except Exception as e:
        print(f"Lỗi khi thêm ticket: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi thêm ticket: {str(e)}")

@app.get("/api/delete-ticket")
async def delete_ticket(ticket: str):
    global ticket_queue
    try:
        service = init_google_sheets()
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!B2:B",
            majorDimension="COLUMNS"
        ).execute()
        
        tickets = result.get('values', [[]])[0]
        
        try:
            row_number = tickets.index(ticket.strip()) + 2
            id_result = service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{SHEET_NAME}!A{row_number}:A{row_number}"
            ).execute()
            id_to_keep = id_result.get('values', [[""]])[0][0]
            
            service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{SHEET_NAME}!A{row_number}:D{row_number}",
                valueInputOption="USER_ENTERED",
                body={"values": [[id_to_keep, "", "", ""]]}
            ).execute()
            
            ticket_queue = deque([(r, e) for r, e in ticket_queue if r != row_number])
            return {"status": True, "message": f"Ticket {ticket} deleted"}
            
        except ValueError:
            return {"status": False, "message": f"Ticket {ticket} not found"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deletion error: {str(e)}")

@app.get("/api/latest-ticket/{id_profile}")
async def get_latest_ticket_by_id(id_profile: str):
    try:
        service = init_google_sheets()
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A2:D",
            majorDimension="ROWS"
        ).execute()
        
        rows = result.get('values', [])
        now = datetime.now(vietnam_tz)
        latest_ticket = None
        latest_time = None
        
        for row in rows:
            if len(row) > 0 and str(row[0]).strip() == id_profile.strip():
                if len(row) < 4 or not row[3]:
                    continue
                    
                try:
                    ticket_time = parse_timestamp(row[3])
                    if latest_time is None or ticket_time > latest_time:
                        latest_time = ticket_time
                        latest_ticket = {
                            "id_profile": row[0],
                            "ticket": row[1] if len(row) > 1 else "",
                            "status": row[2] if len(row) > 2 else "",
                            "timestamp": row[3]
                        }
                except ValueError:
                    continue
        
        if not latest_ticket:
            return {"status": False, "message": f"No tickets found for {id_profile}"}
        
        if now - parse_timestamp(latest_ticket["timestamp"]) > timedelta(minutes=5):
            return {"status": False, "message": "Ticket expired"}
            
        return {"status": True, "ticket": latest_ticket}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lookup error: {str(e)}")

@app.get("/status")
async def check_status():
    return {
        "status": "online",
        "spreadsheet_id": SPREADSHEET_ID,
        "timestamp": datetime.now(vietnam_tz).strftime(TIME_FORMAT)
    }

### Startup ###
@app.on_event("startup")
async def on_startup():
    service = init_google_sheets()
    ensure_headers_and_format(service)
    check_existing_tickets(service)
    asyncio.create_task(cleanup_expired_tickets())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3000, log_level="debug")