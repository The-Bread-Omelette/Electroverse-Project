# ocr_plates.py (EasyOCR + multi-preprocess + digit-fix for Indian plates)
import os
import re
import csv
import argparse
from datetime import datetime

import cv2
import numpy as np
import easyocr


DEFAULT_PLATES_DIR = "data/raw_buffer/plates"
DEFAULT_OUT_CSV = "data/raw_buffer/logs/plate_ocr.csv"

ALNUM_RE = re.compile(r"[^A-Z0-9]+")
PLATE_RE = re.compile(r"^([A-Z]{2})([0-9]{1,2})([A-Z]{1,2})([0-9]{4})$")

# Confusion fixes
DIGIT_FIX = str.maketrans({"O": "0", "I": "1", "L": "1", "Z": "2", "S": "5", "B": "8", "G": "6", "D": "0"})
LETTER_FIX = str.maketrans({"0": "O", "1": "I", "2": "Z", "5": "S", "8": "B", "6": "G"})

# Init once (slow)
reader = easyocr.Reader(["en"], gpu=False)


def clean_text(s: str) -> str:
    return ALNUM_RE.sub("", (s or "").upper())


def fix_india_plate(raw: str) -> str:
    """
    Try to correct common OCR confusions using a common India plate pattern:
    LL DD L{1,2} DDDD (e.g., DL1LAA6957, DL1LX7096)
    """
    t = clean_text(raw)
    if len(t) < 8:
        return t

    # Search a window of 8..10 chars inside the OCR output
    for L in range(8, 11):
        for i in range(0, max(1, len(t) - L + 1)):
            chunk = t[i : i + L]

            # First two letters
            a = chunk[:2].translate(LETTER_FIX)
            rest = chunk[2:]

            # district 1 or 2 digits
            for dlen in (1, 2):
                if len(rest) < dlen + 1 + 4:
                    continue

                b = rest[:dlen].translate(DIGIT_FIX)      # digits
                mid = rest[dlen:-4]                       # 1-2 letters
                c = mid.translate(LETTER_FIX)             # letters
                d = rest[-4:].translate(DIGIT_FIX)        # last 4 digits

                candidate = a + b + c + d
                if PLATE_RE.match(candidate):
                    return candidate

    return t


def sharpness_score(gray: np.ndarray) -> float:
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def preprocess_variants(img_bgr: np.ndarray):
    """
    Produce multiple preprocessed versions.
    OCR sometimes reads digits better on binary images.
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # Upscale (digits need pixels!)
    gray = cv2.resize(gray, None, fx=3.5, fy=3.5, interpolation=cv2.INTER_CUBIC)

    # Variant 1: CLAHE + bilateral (natural)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    v1 = clahe.apply(gray)
    v1 = cv2.bilateralFilter(v1, 7, 60, 60)

    # Variant 2: Otsu threshold
    blur = cv2.GaussianBlur(v1, (5, 5), 0)
    _, v2 = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Variant 3: Adaptive threshold
    v3 = cv2.adaptiveThreshold(
        v1, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 10
    )

    # Variant 4: Inverted Otsu (for yellow plates / dark background cases)
    v4 = cv2.bitwise_not(v2)

    return [("clahe", v1), ("otsu", v2), ("adapt", v3), ("inv_otsu", v4)]


def ocr_easy(img_gray: np.ndarray):
    """
    Run EasyOCR with settings that help digits, return (text, conf).
    """
    results = reader.readtext(
        img_gray,
        detail=1,
        paragraph=False,
        allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        decoder="beamsearch",
        beamWidth=10,
        text_threshold=0.5,
        low_text=0.3,
        contrast_ths=0.1,
        adjust_contrast=0.7,
    )

    if not results:
        return "", 0.0

    parts = []
    for bbox, txt, conf in results:
        txt_c = clean_text(txt)
        if not txt_c:
            continue
        xs = [p[0] for p in bbox]
        cx = sum(xs) / 4.0
        parts.append((cx, txt_c, float(conf)))

    if not parts:
        return "", 0.0

    parts.sort(key=lambda x: x[0])
    joined = "".join([p[1] for p in parts])
    avg_conf = sum([p[2] for p in parts]) / len(parts)

    return joined, avg_conf


def plate_score(text: str, conf: float) -> float:
    """
    Prefer:
    - looks like Indian plate pattern
    - longer text
    - higher confidence
    """
    t = clean_text(text)
    base = len(t) * max(0.0, conf)

    # bonus if matches common plate regex
    if PLATE_RE.match(t):
        base += 10.0

    return base


def iter_images(folder: str):
    for f in sorted(os.listdir(folder)):
        if f.lower().endswith((".jpg", ".jpeg", ".png")):
            yield f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plates-dir", default=DEFAULT_PLATES_DIR)
    ap.add_argument("--out-csv", default=DEFAULT_OUT_CSV)
    ap.add_argument("--min-len", type=int, default=6)
    ap.add_argument("--debug", action="store_true", help="print extra debug info")
    args = ap.parse_args()

    if not os.path.isdir(args.plates_dir):
        raise RuntimeError(f"Plates folder not found: {args.plates_dir}")

    os.makedirs(os.path.dirname(args.out_csv), exist_ok=True)

    rows = []
    total = 0
    good = 0

    for fname in iter_images(args.plates_dir):
        total += 1
        path = os.path.join(args.plates_dir, fname)
        img = cv2.imread(path)
        if img is None:
            print(f"⚠️ {fname} -> could not read")
            continue

        best_text = ""
        best_conf = 0.0
        best_tag = ""
        best_s = -1.0

        for tag, proc in preprocess_variants(img):
            # Skip very blurry variants quickly
            s = sharpness_score(proc)
            text, conf = ocr_easy(proc)

            # Apply India plate correction (helps digits a LOT)
            fixed = fix_india_plate(text)

            score = plate_score(fixed, conf)

            if args.debug:
                print(f"   [{tag}] raw={text} fixed={fixed} conf={conf:.2f} sharp={s:.1f} score={score:.2f}")

            if score > plate_score(best_text, best_conf):
                best_text, best_conf, best_tag, best_s = fixed, conf, tag, s

        # Filter junk
        if len(best_text) < args.min_len:
            best_text = ""
            best_conf = 0.0

        if best_text:
            good += 1
            print(f"✅ {fname} -> {best_text} ({best_conf:.2f}) [{best_tag}]")
        else:
            print(f"✅ {fname} -> (no read)")

        rows.append([
            fname,
            best_text,
            f"{best_conf:.4f}",
            best_tag,
            f"{best_s:.1f}",
            datetime.now().isoformat(timespec="seconds")
        ])

    with open(args.out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["filename", "plate_text", "confidence", "best_variant", "sharpness", "processed_at"])
        w.writerows(rows)

    print("\nDONE ✅")
    print("Images processed:", total)
    print("Plates read:", good)
    print("Saved CSV:", args.out_csv)


if __name__ == "__main__":
    main()