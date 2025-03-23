import cv2
import requests
import numpy as np
from io import BytesIO
import os

class PuzzleCaptchaSolver:
    def __init__(self, gap_image_url, bg_image_url, output_image_path, gap_image_folder="gap_image"):
        self.gap_image_url = gap_image_url
        self.bg_image_url = bg_image_url
        self.output_image_path = output_image_path
        self.gap_image_folder = gap_image_folder
        # Ensure the gap_image folder exists
        if not os.path.exists(self.gap_image_folder):
            os.makedirs(self.gap_image_folder)
        # Ensure the result folder exists
        result_folder = os.path.dirname(self.output_image_path)
        if result_folder and not os.path.exists(result_folder):
            os.makedirs(result_folder)

    def download_image(self, url):
        """
        Downloads an image from a URL and converts it to a cv2-compatible format.

        :param url: The URL of the image to download.
        :return: An image array in cv2 format.
        """
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"Failed to download image from {url}")
        image_bytes = BytesIO(response.content)
        img_array = np.frombuffer(image_bytes.read(), np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        return img

    def remove_whitespace(self, image):
        """
        Removes whitespace from an image by cropping it to the area containing non-whitespace pixels.

        :param image: A numpy array representing the image.
        :return: An image array representing the cropped image without whitespace.
        """
        min_x, min_y, max_x, max_y = 255, 255, 0, 0
        rows, cols, channel = image.shape
        for x in range(1, rows):
            for y in range(1, cols):
                if len(set(image[x, y])) >= 2:
                    min_x, min_y = min(x, min_x), min(y, min_y)
                    max_x, max_y = max(x, max_x), max(y, max_y)
        whitespace_removed_img = image[min_x:max_x, min_y:max_y]
        return whitespace_removed_img

    def apply_edge_detection(self, img):
        """
        Applies edge detection on the given image.

        :param img: The input image.
        :return: The image with edges highlighted.
        """
        grayscale_img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(grayscale_img, 100, 200)
        edges_rgb = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
        return edges_rgb

    def is_duplicate(self, new_image, existing_image_path):
        """
        Checks if the new image is a duplicate of an existing image by comparing pixel values.

        :param new_image: The new processed gap image (numpy array).
        :param existing_image_path: Path to an existing image in the gap_image folder.
        :return: True if the images are duplicates, False otherwise.
        """
        existing_image = cv2.imread(existing_image_path)
        if existing_image is None:
            return False

        # Check if the shapes match
        if new_image.shape != existing_image.shape:
            return False

        # Compare pixel values
        difference = cv2.absdiff(new_image, existing_image)
        # If the sum of differences is very small (or zero), the images are considered duplicates
        return np.sum(difference) == 0

    def save_processed_gap(self, processed_gap):
        """
        Saves the processed gap image to the gap_image folder with a unique name, but only if it's not a duplicate.

        :param processed_gap: The processed gap image (numpy array).
        :return: The path to the saved image, or the path to the existing duplicate.
        """
        # Check for duplicates in the gap_image folder
        for filename in os.listdir(self.gap_image_folder):
            if filename.startswith("image_gap_") and filename.endswith(".png"):
                existing_image_path = os.path.join(self.gap_image_folder, filename)
                if self.is_duplicate(processed_gap, existing_image_path):
                    return existing_image_path  # Return the path of the existing duplicate

        # If no duplicate is found, save the image with a unique name
        i = 1
        while True:
            gap_image_path = os.path.join(self.gap_image_folder, f"image_gap_{i}.png")
            if not os.path.exists(gap_image_path):
                break
            i += 1
        cv2.imwrite(gap_image_path, processed_gap)
        return gap_image_path

    def find_position_of_slide(self, slide_pic, background_pic, output_path=None):
        """
        Find the position of the slide on the background picture.

        :param slide_pic: The slide picture to find.
        :param background_pic: The background picture to search in.
        :param output_path: Optional path to save the result image.
        :return: A tuple of (x-coordinate, confidence score).
        """
        tpl_height, tpl_width = slide_pic.shape[:2]
        result = cv2.matchTemplate(background_pic, slide_pic, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        tl = max_loc
        br = (tl[0] + tpl_width, tl[1] + tpl_height)

        if output_path:
            temp_bg = background_pic.copy()
            cv2.rectangle(temp_bg, tl, br, (0, 0, 255), 2)
            cv2.imwrite(output_path, temp_bg)

        return tl[0], max_val

    def evaluate_all_gaps(self, background_pic):
        """
        Evaluates all processed gap images in the gap_image folder to find the best match.

        :param background_pic: The edge-detected background image.
        :return: A dictionary containing the best position, confidence, and the corresponding gap image path.
        """
        best_position = None
        best_confidence = -float('inf')
        best_gap_path = None

        # Iterate through all images in the gap_image folder
        for filename in os.listdir(self.gap_image_folder):
            if filename.startswith("image_gap_") and filename.endswith(".png"):
                gap_path = os.path.join(self.gap_image_folder, filename)
                gap_image = cv2.imread(gap_path)
                if gap_image is not None:
                    position, confidence = self.find_position_of_slide(gap_image, background_pic)
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_position = position
                        best_gap_path = gap_path

        # If a best match was found, save the result image for that match
        if best_gap_path:
            gap_image = cv2.imread(best_gap_path)
            self.find_position_of_slide(gap_image, background_pic, self.output_image_path)

        return {
            "best_position": best_position,
            "best_confidence": best_confidence,
            "best_gap_image": best_gap_path
        }

    def discern(self):
        """
        Performs the discernment process to find the position of the slide in the given images.
        Also saves the processed gap image (if not a duplicate) and evaluates all processed gaps.

        :return: A dictionary containing the best position, confidence, and the best gap image.
        """
        # Download images from URLs
        gap_image = self.download_image(self.gap_image_url)
        bg_image = self.download_image(self.bg_image_url)

        # Process the gap image
        gap_image_processed = self.remove_whitespace(gap_image)
        edge_detected_gap = self.apply_edge_detection(gap_image_processed)
        edge_detected_bg = self.apply_edge_detection(bg_image)

        # Save the processed gap image (if not a duplicate)
        saved_gap_path = self.save_processed_gap(edge_detected_gap)

        # Evaluate all gap images in the folder
        result = self.evaluate_all_gaps(edge_detected_bg)

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

    solver = PuzzleCaptchaSolver(
        gap_image_url=gap_url,
        bg_image_url=bg_url,
        output_image_path=output_path
    )
    result = solver.discern()

    if result["best_position"] is not None:
        print(f"Vị trí tốt nhất của slide: {result['best_position']}")
        print(f"Độ tin cậy: {result['best_confidence']}")
        print(f"Ảnh gap đã sử dụng: {result['best_gap_image']}")
        print(f"URL của ảnh gap: {result['gap_url']}")
        print(f"Ảnh kết quả: {result['result_image']}")
    else:
        print("Không tìm thấy ảnh gap phù hợp trong thư mục gap_image.")