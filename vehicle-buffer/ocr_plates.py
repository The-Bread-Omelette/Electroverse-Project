import os
import re
import csv
import argparse
from datetime import datetime

import cv2
import numpy as np

from paddleocr import PaddleOCR


DEFAULT_PLATES_DIR = "data/raw_buffer/plates"
DEFAULT_OUT_CSV = "data/raw_buffer/logs/plate_ocr_bestframe.csv"

ALNUM_RE = re.compile(r"[^A-Z0-9]+")

# PaddleOCR with angle classifier (VERY important for tilted plates)
ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)


def clean_text(s: str) -> str:
    s = (s or "").upper()
    return ALNUM_RE.sub("", s)


def sharpness_score(gray: np.ndarray) -> float:
    # Higher = sharper (less blur)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def enhance_for_ocr(img_bgr: np.ndarray) -> np.ndarray:
    # Light enhancement only (PaddleOCR usually prefers natural-ish images)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)

    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    # mild denoise
    gray = cv2.bilateralFilter(gray, 7, 60, 60)

    return gray


def plate_key_from_filename(fname: str) -> str:
    # plate_..._vid-1.jpg -> vid-1
    base = os.path.splitext(fname)[0]
    toks = base.split("_")
    return toks[-1] if len(toks) >= 2 else base


def iter_plate_images(folder: str):
    for name in sorted(os.listdir(folder)):
        if name.lower().endswith((".jpg", ".jpeg", ".png")):
            yield name


def paddle_read_text(img_gray_or_bgr: np.ndarray) -> tuple[str, float]:
    """
    Returns (joined_text, avg_conf)
    PaddleOCR output format:
      [ [ [box], (text, score) ], ... ]
    """
    res = ocr.ocr(img_gray_or_bgr, cls=True)
    if not res or not res[0]:
        return "", 0.0

    pieces = []
    confs = []

    # join left-to-right by box x-center
    items = []
    for line in res[0]:
        box = line[0]
        txt, score = line[1]
        txt_c = clean_text(txt)
        if not txt_c:
            continue
        xs = [p[0] for p in box]
        cx = sum(xs) / len(xs)
        items.append((cx, txt_c, float(score)))

    if not items:
        return "", 0.0

    items.sort(key=lambda x: x[0])
    joined = "".join([x[1] for x in items])
    avg_conf = sum([x[2] for x in items]) / len(items)
    return joined, avg_conf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plates-dir", default=DEFAULT_PLATES_DIR)
    ap.add_argument("--out-csv", default=DEFAULT_OUT_CSV)
    ap.add_argument("--topk", type=int, default=3, help="Try OCR on top K sharpest frames per vehicle")
    ap.add_argument("--debug-best", action="store_true", help="Save the chosen best frame per vehicle")
    args = ap.parse_args()

    plates_dir = args.plates_dir
    out_csv = args.out_csv

    if not os.path.isdir(plates_dir):
        raise RuntimeError(f"Plates folder not found: {plates_dir}")

    os.makedirs(os.path.dirname(out_csv), exist_ok=True)

    # 1) Group files by vehicle key
    groups = {}
    for fname in iter_plate_images(plates_dir):
        k = plate_key_from_filename(fname)
        groups.setdefault(k, []).append(fname)

    debug_dir = os.path.join(os.path.dirname(out_csv), "best_frames_debug")
    if args.debug_best:
        os.makedirs(debug_dir, exist_ok=True)

    print("RUNNING OCR (BEST-FRAME + PADDLEOCR) ✅")
    print("Groups:", len(groups))

    out_rows = []

    for key, files in sorted(groups.items()):
        scored = []

        # 2) Score each crop by sharpness
        for fname in files:
            path = os.path.join(plates_dir, fname)
            img = cv2.imread(path)
            if img is None:
                continue
            enh = enhance_for_ocr(img)
            s = sharpness_score(enh)
            scored.append((s, fname, img, enh))

        if not scored:
            out_rows.append([key, "", "0.0", "", 0, datetime.now().isoformat(timespec="seconds")])
            continue

        scored.sort(key=lambda x: x[0], reverse=True)
        candidates = scored[: max(1, args.topk)]

        best_text = ""
        best_conf = 0.0
        best_fname = candidates[0][1]
        best_sharp = candidates[0][0]

        # 3) OCR only on top-K sharpest
        for s, fname, img_bgr, enh_gray in candidates:
            text, conf = paddle_read_text(enh_gray)

            # Filter junk
            if len(text) < 6:
                continue

            # choose by (len, conf) combo
            score = len(text) * conf
            best_score = (len(best_text) * best_conf) if best_text else 0.0
            if score > best_score:
                best_text, best_conf = text, conf
                best_fname, best_sharp = fname, s

        if args.debug_best:
            # save the sharpest candidate we used (even if text empty)
            _, _, img_bgr, _ = candidates[0]
            cv2.imwrite(os.path.join(debug_dir, f"{key}_{best_fname}"), img_bgr)

        print(f"{key}: best={best_text} conf={best_conf:.2f} sharp={best_sharp:.1f} file={best_fname}")
        out_rows.append([key, best_text, f"{best_conf:.4f}", best_fname, f"{best_sharp:.1f}",
                         datetime.now().isoformat(timespec="seconds")])

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["group_key", "plate_text", "confidence", "best_frame_file", "sharpness", "processed_at"])
        w.writerows(out_rows)

    print("\nDONE ✅ Saved:", out_csv)


if __name__ == "__main__":
    main()
