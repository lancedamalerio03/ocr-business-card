
import io
import numpy as np
from PIL import Image
import pytesseract
import cv2

from .extract_utils import parse_with_gpt

def process_uploaded_image(uploaded_file, api_key: str, model: str = 'gpt-4o-mini') -> list[dict]:
    """
    1. Load image from Streamlit uploader
    2. Run Tesseract OCR to get raw text lines
    3. Send those lines to GPT for structured parsing
    """
    try:
        # — Load into PIL, convert to RGB
        pil_img = Image.open(io.BytesIO(uploaded_file.getvalue())).convert("RGB")
        
        # Convert PIL to numpy array for OpenCV processing
        img_arr = np.array(pil_img)
        
        # Optional: Improve image quality for better OCR
        # Convert to grayscale
        gray = cv2.cvtColor(img_arr, cv2.COLOR_RGB2GRAY)
        
        # Apply noise reduction and sharpening
        denoised = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # Convert back to PIL Image for Tesseract
        processed_img = Image.fromarray(denoised)
        
        # — Tesseract OCR: Extract text
        # Use custom config for better results
        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789@.,()-+/:; '
        
        # Extract text
        extracted_text = pytesseract.image_to_string(processed_img, config=custom_config)
        
        # Split into lines and clean up
        raw_lines = [line.strip() for line in extracted_text.split('\n') if line.strip()]
        
        # Remove very short lines (likely OCR artifacts)
        raw_lines = [line for line in raw_lines if len(line) > 2]
        
        # — GPT parsing (returns list of dicts) with provided API key and model
        cards = parse_with_gpt(raw_lines, api_key, model)
        return cards
        
    except Exception as e:
        print(f"Error in process_uploaded_image: {e}")
        # Return empty list if processing fails
        return []