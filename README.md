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
git clone https://github.com/huyfpl/Puzzle-Captcha-Solver.git
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

