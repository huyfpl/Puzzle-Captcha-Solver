import cv2
import requests
import numpy as np
from io import BytesIO
import os
import json

class PuzzleCaptchaSolver:
    def __init__(self, gap_image_url, bg_image_url, output_image_path, gap_image_folder="gap_image", json_path="captchar.json"):
        self.gap_image_url = gap_image_url
        self.bg_image_url = bg_image_url
        self.output_image_path = output_image_path
        self.gap_image_folder = gap_image_folder
        self.json_path = json_path
        
        if not os.path.exists(self.gap_image_folder):
            os.makedirs(self.gap_image_folder)
        
        result_folder = os.path.dirname(self.output_image_path)
        if result_folder and not os.path.exists(result_folder):
            os.makedirs(result_folder)
        
        if not os.path.exists(self.json_path):
            raise FileNotFoundError(f"File {self.json_path} không tồn tại. Vui lòng cung cấp file captchar.json.")

    def download_image(self, url):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                raise Exception(f"Tải ảnh thất bại từ {url}. Mã trạng thái: {response.status_code}")
            img_array = np.frombuffer(BytesIO(response.content).read(), np.uint8)
            image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            if image is None:
                raise Exception(f"Không thể giải mã ảnh từ {url}")
            return image
        except Exception as e:
            raise

    def remove_whitespace(self, image, threshold=30):
        """
        Xóa nền trắng hoặc gần trắng khỏi ảnh background
        Parameters:
            image: Ảnh đầu vào (BGR)
            threshold: Ngưỡng để xác định màu gần trắng
        Returns:
            Ảnh đã được cắt bỏ nền
        """
        # Chuyển sang không gian màu HSV
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Xác định phạm vi màu trắng/ gần trắng trong HSV
        lower_white = np.array([0, 0, 255 - threshold])
        upper_white = np.array([180, threshold, 255])
        mask = cv2.inRange(hsv, lower_white, upper_white)
        
        # Đảo ngược mask để giữ vùng nội dung
        mask = cv2.bitwise_not(mask)
        
        # Tìm contours của vùng nội dung
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return image  # Trả về ảnh gốc nếu không tìm thấy nội dung
        
        # Tính bounding box bao quanh tất cả contours
        x_min, y_min = image.shape[1], image.shape[0]
        x_max, y_max = 0, 0
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            x_min = min(x_min, x)
            y_min = min(y_min, y)
            x_max = max(x_max, x + w)
            y_max = max(y_max, y + h)
        
        # Thêm padding
        padding = 5
        x_min = max(0, x_min - padding)
        y_min = max(0, y_min - padding)
        x_max = min(image.shape[1], x_max + padding)
        y_max = min(image.shape[0], y_max + padding)
        
        # Cắt ảnh
        cropped = image[y_min:y_max, x_min:x_max]
        return cropped if cropped.size > 0 else image

    def apply_edge_detection(self, img):
        grayscale_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(grayscale_img, 100, 200)
        return cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)

    def extract_thin_outline(self, image):
        grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(grayscale, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            raise Exception("Không tìm thấy đường viền nào trong ảnh gap.")
        
        mask = np.zeros_like(grayscale)
        cv2.drawContours(mask, contours, -1, (255), thickness=cv2.FILLED)
        
        kernel = np.ones((3, 3), np.uint8)
        eroded_mask = cv2.erode(mask, kernel, iterations=2)
        outline_mask = mask - eroded_mask
        
        result = np.zeros_like(image)
        result[outline_mask == 255] = [255, 255, 255]
        
        y_coords, x_coords = np.where(outline_mask == 255)
        if len(x_coords) == 0 or len(y_coords) == 0:
            raise Exception("Không tìm thấy viền sau khi xử lý.")
        
        x_min, x_max = x_coords.min(), x_coords.max()
        y_min, y_max = y_coords.min(), y_coords.max()
        return result[y_min:y_max + 1, x_min:x_max + 1]

    def is_duplicate(self, new_image, existing_image_path):
        existing_image = cv2.imread(existing_image_path)
        if existing_image is None:
            return False
        if new_image.shape != existing_image.shape:
            return False
        difference = cv2.absdiff(new_image, existing_image)
        return np.sum(difference) == 0

    def save_processed_gap(self, processed_gap):
        for filename in os.listdir(self.gap_image_folder):
            if filename.startswith("image_gap_") and filename.endswith(".png"):
                existing_image_path = os.path.join(self.gap_image_folder, filename)
                if self.is_duplicate(processed_gap, existing_image_path):
                    return existing_image_path
        
        i = 1
        while True:
            gap_image_path = os.path.join(self.gap_image_folder, f"image_gap_{i}.png")
            if not os.path.exists(gap_image_path):
                break
            i += 1
        
        cv2.imwrite(gap_image_path, processed_gap)
        return gap_image_path

    def find_position_of_slide(self, slide_pic, background_pic, draw_on_image, draw_rectangle=False):
        tpl_height, tpl_width = slide_pic.shape[:2]
        result = cv2.matchTemplate(background_pic, slide_pic, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        bottom_right = (max_loc[0] + tpl_width, max_loc[1] + tpl_height)
        
        offset = min(0.357, round(tpl_width / 20, 3))
        
        if draw_rectangle and self.output_image_path:
            top_left = (int(max_loc[0] + offset), int(max_loc[1] + offset))
            bottom_right_adjusted = (int(bottom_right[0] - offset), int(bottom_right[1] - offset))
            cv2.rectangle(draw_on_image, top_left, bottom_right_adjusted, (0, 0, 255), 1)
            cv2.imwrite(self.output_image_path, draw_on_image)
        
        final_position = round(max_loc[0] + offset, 3)
        return final_position, max_val

    def evaluate_all_gaps(self, background_pic, draw_on_image):
        best_position = None
        best_confidence = -float('inf')
        best_gap_path = None
        
        for filename in os.listdir(self.gap_image_folder):
            if filename.startswith("image_gap_") and filename.endswith(".png"):
                gap_path = os.path.join(self.gap_image_folder, filename)
                gap_image = cv2.imread(gap_path)
                if gap_image is not None:
                    position, confidence = self.find_position_of_slide(gap_image, background_pic, draw_on_image, draw_rectangle=False)
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_position = position
                        best_gap_path = gap_path
        
        if best_gap_path:
            gap_image = cv2.imread(best_gap_path)
            self.find_position_of_slide(gap_image, background_pic, draw_on_image, draw_rectangle=True)
        
        return {
            "best_position": best_position,
            "best_confidence": best_confidence,
            "best_gap_image": best_gap_path
        }

    def find_nearest_slider(self, position):
        try:
            with open(self.json_path, 'r') as f:
                data = json.load(f)
            
            if not data:
                raise ValueError("File captchar.json rỗng.")
            
            nearest_puzzle_left = None
            nearest_slider_left = None
            min_distance = float('inf')
            
            for entry in data:
                puzzle_left = entry.get("puzzle_left")
                slider_left = entry.get("slider_left")
                if puzzle_left is None or slider_left is None:
                    continue
                if puzzle_left >= position:
                    distance = puzzle_left - position
                    if distance < min_distance:
                        min_distance = distance
                        nearest_puzzle_left = puzzle_left
                        nearest_slider_left = slider_left
            
            if nearest_puzzle_left is None:
                max_puzzle_left = max(entry["puzzle_left"] for entry in data if "puzzle_left" in entry)
                for entry in data:
                    if entry["puzzle_left"] == max_puzzle_left:
                        nearest_puzzle_left = entry["puzzle_left"]
                        nearest_slider_left = entry["slider_left"]
                        break
            
            return nearest_puzzle_left, nearest_slider_left
        
        except Exception as e:
            return None, None

    def discern(self):
        gap_image = self.download_image(self.gap_image_url)
        processed_gap = self.extract_thin_outline(gap_image)
        saved_gap_path = self.save_processed_gap(processed_gap)
        
        bg_image = self.download_image(self.bg_image_url)
        bg_image_resized = cv2.resize(bg_image, (296, 200), interpolation=cv2.INTER_AREA)
        edge_detected_bg = self.apply_edge_detection(bg_image_resized)
        edge_detected_bg = self.remove_whitespace(edge_detected_bg)
        
        result = self.evaluate_all_gaps(edge_detected_bg, edge_detected_bg)
        
        if result["best_position"] is not None:
            nearest_puzzle_left, nearest_slider_left = self.find_nearest_slider(result["best_position"])
            return {
                "position": result["best_position"],
                "best_confidence": result["best_confidence"],
                "best_gap_image": result["best_gap_image"],
                "gap_url": self.gap_image_url,
                "result_image": self.output_image_path,
                "nearest_puzzle_left": nearest_puzzle_left,
                "nearest_slider_left": nearest_slider_left
            }
        else:
            return {
                "position": None,
                "best_confidence": None,
                "best_gap_image": None,
                "gap_url": self.gap_image_url,
                "result_image": self.output_image_path,
                "nearest_puzzle_left": None,
                "nearest_slider_left": None
            }

if __name__ == "__main__":
    gap_url = input("Nhập URL của ảnh gap (slide): ")
    bg_url = input("Nhập URL của ảnh background: ")
    output_path = "result/result.png"
    
    solver = PuzzleCaptchaSolver(
        gap_image_url=gap_url,
        bg_image_url=bg_url,
        output_image_path=output_path,
        gap_image_folder="gap_image",
        json_path="captcha.json"
    )
    
    result = solver.discern()
    if result["position"] is not None:
        print(f"Vị trí tốt nhất của slide: {result['position']}")
        print(f"Cặp gần nhất trong captchar.json - puzzle_left: {result['nearest_puzzle_left']}, slider_left: {result['nearest_slider_left']}")
    else:
        print("Không tìm thấy vị trí hợp lệ.")

