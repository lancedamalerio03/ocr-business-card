import io
import numpy as np
from PIL import Image
import easyocr

from .extract_utils import parse_with_gpt

# Initialize EasyOCR reader (adjust languages or gpu=True if you have CUDA)
READER = easyocr.Reader(["en"], gpu=False)


def process_uploaded_image(uploaded_file, api_key: str, model: str = 'gpt-4o-mini') -> list[dict]:
    """
    1. Load image from Streamlit uploader
    2. Run EasyOCR to get raw text lines
    3. Send those lines to GPT for structured parsing
    """
    # — Load into PIL, convert to RGB
    pil_img = Image.open(io.BytesIO(uploaded_file.getvalue())).convert("RGB")
    img_arr = np.array(pil_img)

    # — EasyOCR: detail=0 returns just lines of text
    raw_lines = READER.readtext(img_arr, detail=0, paragraph=False)

    # — GPT parsing (returns list of dicts) with provided API key and model
    cards = parse_with_gpt(raw_lines, api_key, model)
    return cards