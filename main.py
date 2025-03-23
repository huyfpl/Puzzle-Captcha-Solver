from fastapi import FastAPI, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pytz
import json
import asyncio
from collections import deque
import uvicorn
from autocaptcha import PuzzleCaptchaSolver  # Import the PuzzleCaptchaSolver class
import os
from pydantic import BaseModel  # Import BaseModel for request validation

app = FastAPI(title="Ticket Tracking API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CREDENTIALS_FILE = 'service_account.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = "1ExRHONdCvGq--lZggVEQFGHhhkMYtCuZiOiOisbWTj0"
SHEET_NAME = 'huy1'
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

ticket_queue = deque()
vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')
sheets_service = None
ticket_cache = []

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
        raise HTTPException(status_code=500, detail=f"Không thể kết nối Google Sheets: {str(e)}")

def ensure_headers_and_format(service):
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range=f"{SHEET_NAME}!A1:C1"
        ).execute()
        headers = result.get('values', [])
        expected_headers = ["Ticket", "Trạng thái", "Cập nhật cuối"]

        if not headers or headers[0] != expected_headers:
            service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{SHEET_NAME}!A1:C1",
                valueInputOption="USER_ENTERED",
                body={"values": [expected_headers]}
            ).execute()

        # Định dạng cột thời gian thành dạng văn bản chuẩn
        service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={
                "requests": [{
                    "repeatCell": {
                        "range": {
                            "sheetId": 0,
                            "startColumnIndex": 2,
                            "endColumnIndex": 3
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
        raise HTTPException(status_code=500, detail=f"Lỗi cấu hình tiêu đề: {str(e)}")

def sync_tickets_with_cache(service):
    global ticket_cache
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range=f"{SHEET_NAME}!A2:C"
        ).execute()
        ticket_cache = result.get('values', [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi đồng bộ cache: {str(e)}")

def parse_timestamp(timestamp_str):
    """Xử lý các định dạng thời gian khác nhau"""
    try:
        # Thử parse định dạng chuẩn
        return vietnam_tz.localize(datetime.strptime(timestamp_str, TIME_FORMAT))
    except ValueError:
        try:
            # Nếu là số thập phân từ Google Sheets (số ngày từ 1899-12-30)
            days = float(timestamp_str.replace(',', '.'))
            base_date = datetime(1899, 12, 30, tzinfo=vietnam_tz)
            return base_date + timedelta(days=days)
        except ValueError:
            raise ValueError(f"Không thể parse thời gian: {timestamp_str}")

def check_existing_tickets(service):
    global ticket_queue, ticket_cache
    try:
        sync_tickets_with_cache(service)
        now = datetime.now(vietnam_tz)
        expired_rows = []

        for i, row in enumerate(ticket_cache, start=2):
            if len(row) < 3:
                print(f"Dòng {i} thiếu dữ liệu, bỏ qua.")
                continue
            timestamp_str = row[2].strip()
            try:
                ticket_time = parse_timestamp(timestamp_str)
                expiry_time = ticket_time + timedelta(minutes=5)
                if now >= expiry_time:
                    expired_rows.append(i)
                else:
                    ticket_queue.append((i, expiry_time))
            except ValueError as e:
                print(f"Lỗi parse thời gian tại dòng {i}: {timestamp_str} - {str(e)}")
                continue

        if expired_rows:
            for row in sorted(expired_rows, reverse=True):
                service.spreadsheets().values().clear(
                    spreadsheetId=SPREADSHEET_ID,
                    range=f"{SHEET_NAME}!A{row}:C{row}"
                ).execute()
                ticket_cache.pop(row - 2)
                print(f"Đã xóa ticket hết hạn tại dòng {row} khi khởi động")

    except Exception as e:
        print(f"Lỗi khi kiểm tra ticket hiện có: {str(e)}")

async def cleanup_expired_tickets():
    global ticket_queue, ticket_cache
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
                    service.spreadsheets().values().clear(
                        spreadsheetId=SPREADSHEET_ID,
                        range=f"{SHEET_NAME}!A{row}:C{row}"
                    ).execute()
                    if row - 2 < len(ticket_cache):
                        ticket_cache.pop(row - 2)
                    print(f"Đã xóa ticket tại dòng {row}")

            await asyncio.sleep(10)
        except Exception as e:
            print(f"Lỗi trong cleanup: {str(e)}")
            await asyncio.sleep(10)

@app.post("/api/add-ticket")
async def add_ticket(ticket: str = Form(...)):
    global ticket_queue, ticket_cache
    try:
        service = init_google_sheets()
        ensure_headers_and_format(service)

        now = datetime.now(vietnam_tz)
        expiry = now + timedelta(minutes=5)
        timestamp = now.strftime(TIME_FORMAT)

        values = [[ticket, "Mới", timestamp]]
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A:C",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": values}
        ).execute()

        ticket_cache.append([ticket, "Mới", timestamp])
        row_count = len(ticket_cache) + 1
        ticket_queue.append((row_count, expiry))
        print(f"Thêm ticket mới tại dòng {row_count}, expiry = {expiry}")

        return {"status": True, "message": "Ticket đã được thêm"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi thêm ticket: {str(e)}")

@app.get("/api/delete-ticket")
async def delete_ticket(ticket: str):
    global ticket_queue, ticket_cache
    try:
        service = init_google_sheets()
        if not ticket_cache:
            sync_tickets_with_cache(service)

        row_to_delete = None
        for i, row in enumerate(ticket_cache, start=2):
            if len(row) >= 1 and row[0] == ticket:
                row_to_delete = i
                break

        if row_to_delete is None:
            return {"status": False, "message": f"Không tìm thấy ticket {ticket}"}

        service.spreadsheets().values().clear(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A{row_to_delete}:C{row_to_delete}"
        ).execute()
        
        ticket_cache.pop(row_to_delete - 2)
        ticket_queue = deque([(row, expiry) for row, expiry in ticket_queue if row != row_to_delete])
        
        print(f"Đã xóa ticket {ticket} tại dòng {row_to_delete}")
        return {"status": True, "message": f"Đã xóa ticket {ticket}"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xóa ticket: {str(e)}")

@app.get("/api/latest-ticket")
async def get_latest_ticket():
    try:
        service = init_google_sheets()
        if not ticket_cache:
            sync_tickets_with_cache(service)
        
        if not ticket_cache:
            return {"status": False, "ticket": None, "message": "Không có ticket nào"}
        
        latest_row = ticket_cache[-1]
        if len(latest_row) < 3:
            raise HTTPException(status_code=500, detail="Dữ liệu ticket không hợp lệ")
            
        now = datetime.now(vietnam_tz)
        timestamp_str = latest_row[2].strip()
        
        try:
            ticket_time = parse_timestamp(timestamp_str)
            time_diff = now - ticket_time
            
            if time_diff > timedelta(minutes=3):
                return {"status": False, "ticket": None, "message": "Ticket mới nhất đã quá 5 phút"}
                
            ticket_data = {
                "ticket": latest_row[0],
                "status": latest_row[1],
                "timestamp": ticket_time.strftime(TIME_FORMAT)
            }
            return {"status": True, "ticket": ticket_data}
            
        except ValueError as e:
            raise HTTPException(status_code=500, detail=f"Lỗi parse thời gian: {str(e)}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy ticket mới nhất: {str(e)}")

class CaptchaRequest(BaseModel):
    shadow: str  # URL of the shadow (gap) image
    back: str    # URL of the background image

@app.post("/api/solve-captcha")
async def solve_captcha(request: CaptchaRequest):
    """
    Solve the captcha by processing the shadow and background image URLs.

    :param request: A JSON object containing 'shadow' and 'back' URLs.
    :return: The x-coordinate of the slide position.
    """
    try:
        # Define the output path for the result image
        output_path = os.path.join("result", "captcha_result.png")
        os.makedirs("result", exist_ok=True)  # Ensure the result directory exists

        # Initialize the PuzzleCaptchaSolver
        solver = PuzzleCaptchaSolver(
            gap_image_url=request.shadow,
            bg_image_url=request.back,
            output_image_path=output_path
        )

        # Solve the captcha
        result = solver.discern()

        # Return only the slide position
        return {
            "status": True,
            "position": result["position"],
            "message": "Captcha solved successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error solving captcha: {str(e)}")

@app.get("/status")
async def check_status():
    return {
        "status": "online",
        "spreadsheet_id": SPREADSHEET_ID,
        "spreadsheet_url": f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}",
        "timestamp": datetime.now().strftime(TIME_FORMAT)
    }

@app.on_event("startup")
async def on_startup():
    service = init_google_sheets()
    ensure_headers_and_format(service)
    check_existing_tickets(service)
    asyncio.create_task(cleanup_expired_tickets())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3000, log_level="debug")