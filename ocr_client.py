import base64
import json
import requests

OCR_ENDPOINT = "https://api.ocr.space/parse/image"

def ocr_image_to_text(img_bytes: bytes, api_key: str) -> tuple[bool, str, str]:
    """Call OCR.space with an in-memory PNG/JPG and return (ok, text, error)."""
    try:
        b64 = base64.b64encode(img_bytes).decode("ascii")
        data = {
            "base64Image": "data:image/png;base64," + b64,
            "OCREngine": 2,
            "scale": True,
            "isOverlayRequired": False,
            "detectOrientation": True,
            "language": "eng",
        }
        headers = {"apikey": api_key}
        resp = requests.post(OCR_ENDPOINT, data=data, headers=headers, timeout=60)
        resp.raise_for_status()
        j = resp.json()
        if not j.get("IsErroredOnProcessing") and j.get("ParsedResults"):
            text = "\n".join([r.get("ParsedText", "") for r in j["ParsedResults"]])
            return True, text, ""
        return False, "", j.get("ErrorMessage") or "Unknown OCR error"
    except Exception as e:
        return False, "", str(e)
