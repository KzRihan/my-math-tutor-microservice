from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import io
from PIL import Image, ImageEnhance
import numpy as np
from pix2tex.cli import LatexOCR
from paddleocr import PaddleOCR
import uvicorn
from typing import List
import cv2
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Math OCR Service - Production Ready")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global models (loaded once)
latex_ocr = LatexOCR()
# Initialize PaddleOCR with settings compatible with your installed version.
# Many keyword arguments (like `show_log`, `det`, `rec`) are not supported in
# your version's constructor, so we only pass the safe ones here.
paddle_ocr = PaddleOCR(
    use_textline_orientation=True,
    lang='en',
    device="cpu"
)

# Lazy initialization of structure engine (may fail if paddlex[ocr] not installed)
structure_engine = None

def get_structure_engine():
    """Lazy initialization of PPStructureV3"""
    global structure_engine
    if structure_engine is None:
        try:
            try:
                from paddleocr import PPStructureV3 as PPStructureImpl
            except Exception:
                try:
                    from paddleocr import PPStructure as PPStructureImpl
                except Exception:
                    PPStructureImpl = None

            if PPStructureImpl is None:
                raise ImportError("PPStructureV3/PPStructure not available in this paddleocr version")

            structure_engine = PPStructureImpl(lang='en')
            logger.info("Structure engine initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize structure engine: {e}. Using fallback OCR only.")
            structure_engine = False  # Mark as failed
    return structure_engine if structure_engine is not False else None

def preprocess_image(image: Image.Image) -> Image.Image:
    """Enhance image for better OCR accuracy"""
    # Ensure RGB mode
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Resize if image is too small (helps OCR)
    width, height = image.size
    if width < 300 or height < 100:
        scale = max(300 / width, 100 / height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # Light contrast enhancement (less aggressive)
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.2)
    
    return image

def crop_region(image: np.ndarray, bbox: List[List[int]]) -> Image.Image:
    """Crop specific region from image using bbox"""
    if not bbox:
        return Image.fromarray(image)
    
    pts = np.array(bbox, dtype=np.int32)
    x, y, w, h = cv2.boundingRect(pts)
    cropped = image[y:y+h, x:x+w]
    return Image.fromarray(cropped)

def fallback_ocr(image_input) -> str:
    """Pure text fallback when structure fails"""
    # Handle both PIL Image and numpy array
    if isinstance(image_input, Image.Image):
        image_np = np.array(image_input)
    else:
        image_np = image_input
    
    # Ensure it's a valid numpy array
    if not isinstance(image_np, np.ndarray):
        return ""
    
    try:
        # Use PaddleOCR with proper parameters
        result = paddle_ocr.ocr(image_np, det=True, rec=True)
        
        if result and result[0]:
            # Extract text from all detected lines
            texts = []
            for line in result[0]:
                if line and len(line) >= 2:
                    text = line[1][0] if isinstance(line[1], (list, tuple)) else str(line[1])
                    if text and text.strip():
                        texts.append(text.strip())
            return ' '.join(texts) if texts else ""
    except Exception as e:
        logger.error(f"OCR error: {e}")
        # Try without explicit parameters
        try:
            result = paddle_ocr.ocr(image_np)
            if result and result[0]:
                texts = []
                for line in result[0]:
                    if line and len(line) >= 2:
                        text = line[1][0] if isinstance(line[1], (list, tuple)) else str(line[1])
                        if text and text.strip():
                            texts.append(text.strip())
                return ' '.join(texts) if texts else ""
        except Exception as e2:
            logger.error(f"OCR fallback error: {e2}")
    
    return ""

def text_to_latex(text: str) -> str:
    """
    Convert OCR text to LaTeX-safe text without changing meaning
    """
    text = text.replace("\\", "\\textbackslash ")
    text = text.replace("{", "\\{").replace("}", "\\}")
    text = text.replace("_", "\\_").replace("%", "\\%")
    return f"\\text{{{text}}}"

@app.post("/ocr")
async def ocr_endpoint(
    file: UploadFile = File(...),
    strategy: str = "hybrid",  # hybrid | paddle_only | pix2tex_only
    language: str = "en"
):
    start_time = datetime.now()

    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        original_image = image.copy()
        image = preprocess_image(image)
        image_np = np.array(image)

        blocks = []
        detected_formula = False

        # --------------------------------------------------
        # STRATEGY: PIX2TEX ONLY
        # --------------------------------------------------
        if strategy == "pix2tex_only":
            latex = latex_ocr(image).strip()
            if latex:
                blocks.append({
                    "type": "formula",
                    "latex": latex,
                    "confidence": 0.95,
                    "bbox": []
                })
            else:
                blocks.append({
                    "type": "text",
                    "content": fallback_ocr(image),
                    "confidence": 0.4,
                    "bbox": []
                })

        # --------------------------------------------------
        # STRATEGY: PADDLE ONLY
        # --------------------------------------------------
        elif strategy == "paddle_only":
            text = fallback_ocr(original_image) or fallback_ocr(image)
            if text:
                blocks.append({
                    "type": "text",
                    "content": text.strip(),
                    "confidence": 0.85,
                    "bbox": []
                })

        # --------------------------------------------------
        # STRATEGY: HYBRID (DEFAULT)
        # --------------------------------------------------
        else:
            try:
                struct_engine = get_structure_engine()
                layout_result = struct_engine.predict([image_np])
                layout_items = layout_result.get("result", layout_result)

                for item in layout_items:
                    item_type = item.get("type", "unknown")
                    confidence = float(item.get("confidence", 0.0))
                    bbox = item.get("bbox", [])

                    # -------- TEXT BLOCK --------
                    if item_type == "text" and confidence >= 0.5:
                        text = item["res"].get("text", "").strip()
                        if text:
                            blocks.append({
                                "type": "text",
                                "content": text,
                                "confidence": confidence,
                                "bbox": bbox
                            })

                    # -------- FORMULA BLOCK --------
                    elif item_type in ["formula", "equation"]:
                        crop = crop_region(image_np, bbox)
                        latex = latex_ocr(crop).strip()
                        if latex:
                            detected_formula = True
                            blocks.append({
                                "type": "formula",
                                "latex": latex,
                                "confidence": min(0.98, confidence + 0.1),
                                "bbox": bbox
                            })

            except Exception:
                # Hybrid fallback (preserved)
                text = fallback_ocr(original_image) or fallback_ocr(image)
                if text:
                    blocks.append({
                        "type": "text",
                        "content": text.strip(),
                        "confidence": 0.5,
                        "bbox": []
                    })

        # --------------------------------------------------
        # FINAL FAILSAFE (NEVER EMPTY)
        # --------------------------------------------------
        if not blocks:
            blocks.append({
                "type": "text",
                "content": fallback_ocr(original_image) or "",
                "confidence": 0.3,
                "bbox": []
            })

        # --------------------------------------------------
        # BUILD layout_markdown (STRICT REQUIREMENT)
        # --------------------------------------------------
        markdown_parts = ["# Problem"]
        for block in blocks:
            if block["type"] == "text":
                markdown_parts.append(block["content"])
            elif block["type"] == "formula":
                markdown_parts.append(f"$${block['latex']}$$")

        layout_markdown = "\n".join(markdown_parts)

        # --------------------------------------------------
        # CONFIDENCE
        # --------------------------------------------------
        avg_conf = np.mean([b["confidence"] for b in blocks])
        quality_score = min(1.0, avg_conf + (0.1 if detected_formula else 0))

        return {
            "success": True,
            "blocks": blocks,
            "language_detected": language,
            "layout_markdown": layout_markdown,
            "quality_score": float(quality_score),
            "processing_time_ms": int(
                (datetime.now() - start_time).total_seconds() * 1000
            )
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "blocks": [],
            "layout_markdown": "",
            "processing_time_ms": int(
                (datetime.now() - start_time).total_seconds() * 1000
            )
        }

@app.get("/health")
async def health_check():
    struct_status = "ready" if get_structure_engine() is not None else "unavailable"
    return {
        "status": "healthy",
        "models": {
            "pix2tex": "ready",
            "paddleocr": "ready",
            "structure": struct_status
        },
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8501, log_level="info")
 
