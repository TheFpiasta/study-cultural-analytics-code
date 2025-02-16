# analyzer/utils/easyocr.py
import easyocr

def run_ocr(image_path, reader):
    """Runs OCR on an image and returns extracted text."""

    # Use the already initialized reader
    results = reader.readtext(image_path)

    recognized_text = ""
    total_confidence = 0
    num_confidences = 0

    bounding_boxes = []

    # Process the text and confidence without annotating or saving the image
    for (bbox, text, confidence) in results:
        if confidence <= 0.5:
            continue
            
        recognized_text += f"{text}\n"
        total_confidence += confidence
        num_confidences += 1

        bbox = [(int(coord[0]), int(coord[1])) for coord in bbox]

        bounding_boxes.append({
            'text': text,
            'bbox': bbox
        })

    if num_confidences > 0:
        avg_confidence = total_confidence / num_confidences
    else:
        avg_confidence = 0

    return recognized_text, bounding_boxes
