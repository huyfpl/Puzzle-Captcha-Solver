🧩 PuzzleCaptchaSolver - Giải Captcha dạng kéo thả tự động
PuzzleCaptchaSolver là một dự án Python giúp giải các loại CAPTCHA dạng hình ảnh kéo thả như Geetest3, Geetest4, Binance, DataDome, TikTok và nhiều loại khác. Dự án sử dụng thư viện OpenCV để xử lý ảnh và xác định chính xác vị trí cần kéo của mảnh ghép.

🎯 Tính năng
Xóa khoảng trắng: Tự động cắt bỏ các khoảng trắng không cần thiết trong ảnh.

Phát hiện cạnh: Áp dụng phát hiện cạnh để cải thiện độ chính xác khi ghép ảnh.

Xác định vị trí: Tìm và đánh dấu chính xác vị trí mảnh ghép trên ảnh nền.

🚀 Cài đặt
Clone source:

bash
Sao chép
Chỉnh sửa
git clone https://github.com/vsmutok/Puzzle-Captcha-Solver.git
cd Puzzle-Captcha-Solver
Tạo và kích hoạt môi trường ảo:

bash
Sao chép
Chỉnh sửa
python3 -m venv .venv
source .venv/bin/activate
Cài đặt thư viện cần thiết:

bash
Sao chép
Chỉnh sửa
pip install -r requirements.txt
🧠 Cách sử dụng API
Sau khi server FastAPI được chạy lên (mặc định cổng 3000), bạn có thể gửi yêu cầu POST đến API sau để giải captcha:

📮 Endpoint: POST /api/verify-captcha
✅ Request:
json
Sao chép
Chỉnh sửa
{
  "gap_image_url": "https://static-captcha-sgp.aliyuncs.com/qst/PUZZLE/online/530/4adcf955-9d0a-4cb0-a9ab-95754da9902d/shadow.png",
  "bg_image_url": "https://static-captcha-sgp.aliyuncs.com/qst/PUZZLE/online/530/4adcf955-9d0a-4cb0-a9ab-95754da9902d/back.png"
}
gap_image_url: Đường dẫn tới ảnh mảnh ghép (shadow).

bg_image_url: Đường dẫn tới ảnh nền (background).

output_image_path (tuỳ chọn): Nơi lưu ảnh kết quả (mặc định result/result.png).

gap_image_folder (tuỳ chọn): Thư mục lưu ảnh mảnh ghép.

json_path (tuỳ chọn): File JSON chứa thông tin chi tiết kết quả.

🔁 Response (thành công):
json
Sao chép
Chỉnh sửa
{
  "status": true,
  "message": "Success",
  "result": {
    "position": 153,
    "best_confidence": 0.9876,
    "best_gap_image": "gap_image/4adcf955-slice.png",
    "gap_url": "https://static-captcha-sgp.aliyuncs.com/qst/PUZZLE/online/530/4adcf955-.../shadow.png",
    "result_image": "result/result.png",
    "nearest_puzzle_left": 153,
    "nearest_slider_left": 152
  }
}
❌ Response (thất bại):
json
Sao chép
Chỉnh sửa
{
  "detail": "Failed to solve captcha"
}
💡 Ví dụ dùng bằng curl
bash
Sao chép
Chỉnh sửa
curl -X POST http://0.0.0.0:3000/api/verify-captcha \
-H "Content-Type: application/json" \
-d '{
  "gap_image_url":"https://static-captcha-sgp.aliyuncs.com/qst/PUZZLE/online/530/4adcf955-9d0a-4cb0-a9ab-95754da9902d/shadow.png",
  "bg_image_url":"https://static-captcha-sgp.aliyuncs.com/qst/PUZZLE/online/530/4adcf955-9d0a-4cb0-a9ab-95754da9902d/back.png"
}'
⚙ Các endpoint khác (liên quan đến Google Sheet)
API	Mô tả
POST /api/add-ticket	Thêm ticket mới (qua form)
GET /api/delete-ticket?ticket=abc	Xoá ticket theo nội dung
GET /api/latest-ticket/{id_profile}	Lấy ticket mới nhất theo ID Profile
GET /status	Kiểm tra trạng thái server
⚠️ Lưu ý
Mỗi ticket tồn tại tối đa 5 phút trước khi tự động xóa.

API tự động kết nối với Google Sheet để lưu trữ trạng thái ticket.

📄 Giấy phép
Dự án được cấp phép theo giấy phép MIT.

🛡️ Disclaimer
Dự án này được tạo ra nhằm mục đích học tập và nghiên cứu. Không khuyến khích hoặc chịu trách nhiệm cho bất kỳ hành động vi phạm nào đối với chính sách của các trang web.

Nếu bạn cần thêm bản hướng dẫn mẫu cho Python, Postman, hay JS Fetch thì mình cũng có thể viết luôn nhé!







Bạn đã nói:
thêm các ảnh capcha ở readme cũ và sửa lại giao diện cho đẹp với ngăn cách r


ChatGPT đã nói:
Dưới đây là README đã được viết lại hoàn toàn bằng tiếng Việt, bao gồm hướng dẫn sử dụng API, ví dụ cụ thể, hình ảnh minh họa CAPTCHAs, và có giao diện trình bày rõ ràng, ngăn cách từng phần hợp lý để bạn dễ theo dõi và sử dụng:

🎯 Puzzle Captcha Solver API - Giải Mã Captcha Tự Động bằng Python + FastAPI 🧩
PuzzleCaptchaSolver là một công cụ giải mã captcha dạng ghép hình (puzzle) như Geetest3, Geetest4, Binance, DataDome, TikTok... sử dụng thư viện OpenCV và được tích hợp qua một API đơn giản bằng FastAPI.

✅ Tự động phát hiện vị trí mảnh ghép trong ảnh nền.
✅ Hỗ trợ ảnh từ URL.
✅ Phù hợp để tích hợp vào hệ thống tự động hoá / bot / farm acc.

💡 Tính năng chính
🧼 Xử lý ảnh: Tự động loại bỏ khoảng trắng.

🧠 Edge Detection: Dò biên cạnh để tăng độ chính xác khi khớp mẫu.

🎯 Xác định vị trí mảnh ghép: Trả về vị trí khớp chính xác nhất và tạo ảnh kết quả có highlight.

🌐 API REST: Có thể gọi từ bất kỳ client nào (Python, Postman, JS, ...)

🚀 Hướng dẫn cài đặt
bash
Sao chép
Chỉnh sửa
# 1. Clone dự án
git clone https://github.com/vsmutok/Puzzle-Captcha-Solver.git
cd Puzzle-Captcha-Solver

# 2. Tạo môi trường ảo
python3 -m venv .venv
source .venv/bin/activate

# 3. Cài đặt dependencies
pip install -r requirements.txt

# 4. Chạy server
uvicorn main:app --reload --port 3000
📡 API Giải Captcha
POST /api/verify-captcha
✅ Payload mẫu:
json
Sao chép
Chỉnh sửa
{
  "gap_image_url": "https://static-captcha-sgp.aliyuncs.com/qst/PUZZLE/online/530/4adcf955-9d0a-4cb0-a9ab-95754da9902d/shadow.png",
  "bg_image_url": "https://static-captcha-sgp.aliyuncs.com/qst/PUZZLE/online/530/4adcf955-9d0a-4cb0-a9ab-95754da9902d/back.png"
}
🔁 Phản hồi:
json
Sao chép
Chỉnh sửa
{
  "status": true,
  "message": "Success",
  "result": {
    "position": 147,
    "best_confidence": 0.92,
    "best_gap_image": "gap_image/4adcf955_shadow.png",
    "gap_url": "https://...shadow.png",
    "result_image": "result/result.png",
    "nearest_puzzle_left": 145,
    "nearest_slider_left": 147
  }
}
📌 position: Vị trí mảnh ghép trên ảnh nền.
📸 result_image: Ảnh có rectangle highlight vị trí mảnh ghép (màu đỏ).
📈 best_confidence: Mức độ khớp tốt nhất.

🖼️ Ảnh Minh Hoạ
Ảnh nền	Mảnh ghép	Kết quả
		
🛠️ Các API khác (Quản lý Ticket)
Method	Đường dẫn	Mô tả
POST	/api/add-ticket	Thêm ticket vào Google Sheet
GET	/api/delete-ticket?ticket=...	Xoá ticket khỏi sheet
GET	/api/latest-ticket/{id_profile}	Lấy ticket mới nhất theo ID
GET	/status	Kiểm tra trạng thái server
Các ticket sẽ tự động hết hạn sau 5 phút và được làm sạch bởi background task.

🧪 Test với Postman hoặc cURL
bash
Sao chép
Chỉnh sửa
curl -X POST http://0.0.0.0:3000/api/verify-captcha \
  -H "Content-Type: application/json" \
  -d '{
    "gap_image_url": "https://static-captcha-sgp.aliyuncs.com/qst/PUZZLE/online/530/4adcf955-9d0a-4cb0-a9ab-95754da9902d/shadow.png",
    "bg_image_url": "https://static-captcha-sgp.aliyuncs.com/qst/PUZZLE/online/530/4adcf955-9d0a-4cb0-a9ab-95754da9902d/back.png"
}'
🤝 Cảm ơn
OpenCV – thư viện xử lý ảnh mạnh mẽ.

FastAPI – giúp bạn tạo REST API siêu nhanh.

Google Sheets API – lưu và quản lý ticket dễ dàng qua Google Sheet.

⚠️ Lưu ý
Dự án này được tạo ra với mục đích nghiên cứu học thuật và demo kỹ thuật.
Không khuyến khích sử dụng để vi phạm điều khoản sử dụng của bất kỳ nền tảng nào.
