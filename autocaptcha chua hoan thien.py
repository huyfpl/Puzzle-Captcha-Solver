import cv2
import requests
import numpy as np
from io import BytesIO
import os

class PuzzleCaptchaSolver:
    def __init__(self, gap_image_url, bg_image_url, output_image_path, gap_image_folder="gap_image"):
        """
        Khởi tạo PuzzleCaptchaSolver với các tham số cần thiết.
        
        :param gap_image_url: URL của ảnh gap (slide).
        :param bg_image_url: URL của ảnh background.
        :param output_image_path: Đường dẫn để lưu ảnh kết quả.
        :param gap_image_folder: Thư mục để lưu các ảnh gap đã xử lý.
        """
        self.gap_image_url = gap_image_url
        self.bg_image_url = bg_image_url
        self.output_image_path = output_image_path
        self.gap_image_folder = gap_image_folder
        
        # Tạo thư mục nếu chưa tồn tại
        if not os.path.exists(self.gap_image_folder):
            os.makedirs(self.gap_image_folder)
        result_folder = os.path.dirname(self.output_image_path)
        if result_folder and not os.path.exists(result_folder):
            os.makedirs(result_folder)

    def download_image(self, url):
        """
        Tải ảnh từ URL và chuyển thành numpy array.
        
        :param url: URL của ảnh.
        :return: Ảnh dưới dạng numpy array.
        """
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"Failed to download image from {url}")
        img_array = np.frombuffer(BytesIO(response.content).read(), np.uint8)
        return cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    def extract_thin_outline(self, image):
        """
        Tách viền ngoài của mảnh ghép, tạo đường mảnh, và cắt ảnh theo kích thước của viền.
        
        :param image: Ảnh đầu vào (numpy array).
        :return: Ảnh chỉ chứa đường viền mảnh, đã được cắt theo kích thước của viền.
        """
        # Chuyển ảnh sang grayscale
        grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Áp dụng threshold để tách mảnh ghép khỏi nền
        _, binary = cv2.threshold(grayscale, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Tìm contours (đường viền ngoài)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            raise Exception("No contours found in the gap image")
        
        # Tạo mask ban đầu chứa toàn bộ mảnh ghép
        mask = np.zeros_like(grayscale)
        cv2.drawContours(mask, contours, -1, (255), thickness=cv2.FILLED)
        
        # Thu nhỏ (contract) mask để tạo viền mỏng hơn
        kernel = np.ones((3, 3), np.uint8)
        eroded_mask = cv2.erode(mask, kernel, iterations=2)  # Thu nhỏ khoảng 2px
        
        # Tạo viền mảnh bằng cách lấy hiệu giữa mask gốc và mask đã thu nhỏ
        outline_mask = mask - eroded_mask
        
        # Tạo ảnh kết quả: chỉ giữ lại viền mảnh
        result = np.zeros_like(image)
        result[outline_mask == 255] = [255, 255, 255]  # Đặt viền thành màu trắng
        
        # Tìm bounding box của viền mảnh
        y_coords, x_coords = np.where(outline_mask == 255)
        if len(x_coords) == 0 or len(y_coords) == 0:
            raise Exception("No outline found after processing")
        x_min, x_max = x_coords.min(), x_coords.max()
        y_min, y_max = y_coords.min(), y_coords.max()
        
        # Cắt ảnh theo bounding box
        cropped_result = result[y_min:y_max+1, x_min:x_max+1]
        
        return cropped_result

    def remove_background(self, image):
        """
        Xóa nền của ảnh bằng cách giữ lại đối tượng chính.
        
        :param image: Ảnh đầu vào (numpy array).
        :return: Ảnh với nền đã xóa.
        """
        grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(grayscale, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        mask = np.zeros_like(grayscale)
        cv2.drawContours(mask, contours, -1, (255), thickness=cv2.FILLED)
        result = cv2.bitwise_and(image, image, mask=mask)
        return result

    def apply_edge_detection(self, img):
        """
        Áp dụng edge detection để tìm viền của ảnh.
        
        :param img: Ảnh đầu vào (numpy array).
        :return: Ảnh với các viền được làm nổi bật.
        """
        grayscale = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(grayscale, (3, 3), 0)
        edges = cv2.Canny(blurred, 50, 150)
        return cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

    def is_duplicate(self, new_image, existing_image_path):
        """
        Kiểm tra xem ảnh mới có trùng với ảnh đã lưu hay không.
        
        :param new_image: Ảnh mới (numpy array).
        :param existing_image_path: Đường dẫn đến ảnh đã lưu.
        :return: True nếu trùng, False nếu không.
        """
        existing_image = cv2.imread(existing_image_path)
        if existing_image is None:
            return False
        if new_image.shape != existing_image.shape:
            return False
        difference = cv2.absdiff(new_image, existing_image)
        return np.sum(difference) == 0

    def save_processed_gap(self, processed_gap):
        """
        Lưu ảnh gap đã xử lý vào thư mục, tránh trùng lặp.
        
        :param processed_gap: Ảnh gap đã xử lý (numpy array).
        :return: Đường dẫn đến ảnh đã lưu.
        """
        for filename in os.listdir(self.gap_image_folder):
            if filename.startswith("image_gap_") and filename.endswith(".png"):
                existing_image_path = os.path.join(self.gap_image_folder, filename)
                if self.is_duplicate(processed_gap, existing_image_path):
                    return existing_image_path
        
        # Tìm tên file mới
        i = 1
        while True:
            gap_image_path = os.path.join(self.gap_image_folder, f"image_gap_{i}.png")
            if not os.path.exists(gap_image_path):
                break
            i += 1
        
        # Lưu ảnh
        cv2.imwrite(gap_image_path, processed_gap)
        return gap_image_path

    def find_position_of_slide(self, slide_pic, background_pic, draw_rectangle=False):
        """
        Tìm vị trí của slide trên ảnh background bằng template matching.
        
        :param slide_pic: Ảnh slide (gap).
        :param background_pic: Ảnh background đã xử lý.
        :param draw_rectangle: Nếu True, vẽ hình chữ nhật tại vị trí tìm thấy.
        :return: Vị trí x của slide và độ tin cậy.
        """
        tpl_height, tpl_width = slide_pic.shape[:2]
        result = cv2.matchTemplate(background_pic, slide_pic, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        br = (max_loc[0] + tpl_width, max_loc[1] + tpl_height)
        
        # Chỉ vẽ hình chữ nhật nếu draw_rectangle=True
        if draw_rectangle and self.output_image_path:
            cv2.rectangle(background_pic, max_loc, br, (0, 0, 255), 2)
            cv2.imwrite(self.output_image_path, background_pic)
        
        return max_loc[0], max_val

    def evaluate_all_gaps(self, background_pic, original_bg):
        """
        Đánh giá tất cả các ảnh gap đã lưu để tìm vị trí tốt nhất.
        
        :param background_pic: Ảnh background đã xử lý (dùng để tìm vị trí).
        :param original_bg: Ảnh background gốc (dùng để vẽ hình chữ nhật).
        :return: Dictionary chứa thông tin về vị trí tốt nhất.
        """
        best_position = None
        best_confidence = -float('inf')
        best_gap_path = None
        
        # Thử nghiệm với từng ảnh gap, không vẽ hình chữ nhật
        for filename in os.listdir(self.gap_image_folder):
            if filename.startswith("image_gap_") and filename.endswith(".png"):
                gap_path = os.path.join(self.gap_image_folder, filename)
                gap_image = cv2.imread(gap_path)
                if gap_image is not None:
                    position, confidence = self.find_position_of_slide(gap_image, background_pic, draw_rectangle=False)
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_position = position
                        best_gap_path = gap_path
        
        # Sau khi tìm được vị trí tốt nhất, vẽ một hình chữ nhật duy nhất trên ảnh gốc
        if best_gap_path:
            gap_image = cv2.imread(best_gap_path)
            self.find_position_of_slide(gap_image, original_bg, draw_rectangle=True)
        
        return {
            "best_position": best_position,
            "best_confidence": best_confidence,
            "best_gap_image": best_gap_path
        }

    def discern(self):
        """
        Xử lý ảnh gap và background để tìm vị trí ghép.
        
        :return: Dictionary chứa thông tin về vị trí ghép và các thông số liên quan.
        """
        # Tải ảnh gap và background
        gap_image = self.download_image(self.gap_image_url)
        bg_image = self.download_image(self.bg_image_url)

        # Giữ một bản sao của ảnh background gốc để vẽ hình chữ nhật
        original_bg = bg_image.copy()

        # Xử lý ảnh gap: tách viền mảnh và cắt theo kích thước viền
        processed_gap = self.extract_thin_outline(gap_image)
        
        # Xử lý ảnh background: xóa nền và áp dụng edge detection
        processed_bg = self.remove_background(bg_image)
        edge_detected_bg = self.apply_edge_detection(processed_bg)
        
        # Lưu ảnh gap đã xử lý
        saved_gap_path = self.save_processed_gap(processed_gap)
        
        # Đánh giá vị trí ghép
        result = self.evaluate_all_gaps(edge_detected_bg, original_bg)

        return {
            "position": result["best_position"],
            "best_confidence": result["best_confidence"],
            "best_gap_image": result["best_gap_image"],
            "gap_url": self.gap_image_url,
            "result_image": self.output_image_path
        }

if __name__ == "__main__":
    # Nhập URL từ người dùng
    gap_url = input("Nhập URL của ảnh gap (slide): ")
    bg_url = input("Nhập URL của ảnh background: ")
    output_path = "result/result.png"

    # Khởi tạo solver và chạy
    solver = PuzzleCaptchaSolver(
        gap_image_url=gap_url,
        bg_image_url=bg_url,
        output_image_path=output_path
    )
    result = solver.discern()

    # In kết quả
    if result["best_position"] is not None:
        print(f"Vị trí tốt nhất của slide: {result['best_position']}")
        print(f"Độ tin cậy: {result['best_confidence']}")
        print(f"Ảnh gap đã sử dụng: {result['best_gap_image']}")
        print(f"URL của ảnh gap: {result['gap_url']}")
        print(f"Ảnh kết quả: {result['result_image']}")
    else:
        print("Không tìm thấy ảnh gap phù hợp trong thư mục gap_image.")



