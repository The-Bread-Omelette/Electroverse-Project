import os
import time
import argparse
from collections import deque
from datetime import datetime

import cv2
import pandas as pd
from ultralytics import YOLO


# ------------------ Rolling Buffer Writer ------------------
class RollingBufferWriter:
    """
    Writes frames into chunked video files and keeps only the last N minutes.
    Uses mp4 when possible, falls back to avi if mp4 writer fails (common on WSL).
    """

    def __init__(
        self,
        out_dir: str,
        fps: float,
        frame_size: tuple[int, int],
        chunk_seconds: int,
        keep_minutes: int,
    ):
        self.out_dir = out_dir
        self.fps = float(fps)
        self.w, self.h = frame_size
        self.chunk_seconds = int(chunk_seconds)
        self.keep_seconds = int(keep_minutes * 60)
        self.frames_per_chunk = max(1, int(self.fps * self.chunk_seconds))

        self.cur_writer = None
        self.cur_frame_count = 0
        self.chunk_paths = deque()  # (timestamp, filepath)

        os.makedirs(self.out_dir, exist_ok=True)
        self.mp4_fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.avi_fourcc = cv2.VideoWriter_fourcc(*"XVID")

    def _start_new_chunk(self):
        ts = time.time()
        stamp = datetime.fromtimestamp(ts).strftime("%Y%m%d_%H%M%S")

        # Close previous writer
        if self.cur_writer is not None:
            self.cur_writer.release()

        # Try MP4 first
        mp4_path = os.path.join(self.out_dir, f"chunk_{stamp}.mp4")
        writer = cv2.VideoWriter(mp4_path, self.mp4_fourcc, self.fps, (self.w, self.h))

        # Fallback to AVI if mp4 writer fails (very common on WSL)
        if not writer.isOpened():
            try:
                writer.release()
            except Exception:
                pass

            avi_path = os.path.join(self.out_dir, f"chunk_{stamp}.avi")
            writer = cv2.VideoWriter(avi_path, self.avi_fourcc, self.fps, (self.w, self.h))

            if not writer.isOpened():
                raise RuntimeError(
                    "❌ VideoWriter failed for both MP4 and AVI.\n"
                    "Fix: install ffmpeg and try again:\n"
                    "sudo apt update && sudo apt install -y ffmpeg"
                )

            path = avi_path
        else:
            path = mp4_path

        self.cur_writer = writer
        print(f"[buffer] started new chunk: {path} opened={self.cur_writer.isOpened()}", flush=True)
        if not self.cur_writer.isOpened():
            raise RuntimeError(f"❌ VideoWriter could not open: {path}")

        self.cur_frame_count = 0
        self.chunk_paths.append((ts, path))

    def _cleanup_old(self):
        now = time.time()
        while self.chunk_paths and (now - self.chunk_paths[0][0]) > self.keep_seconds:
            _, old_path = self.chunk_paths.popleft()
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except Exception:
                    pass

    def write(self, frame):
        if self.cur_writer is None:
            self._start_new_chunk()

        self.cur_writer.write(frame)
        self.cur_frame_count += 1

        if self.cur_frame_count >= self.frames_per_chunk:
            self._start_new_chunk()

        self._cleanup_old()

    def close(self):
        if self.cur_writer is not None:
            self.cur_writer.release()
            self.cur_writer = None


# ------------------ Helpers ------------------
def safe_crop(img, x1, y1, x2, y2):
    h, w = img.shape[:2]
    x1 = max(0, min(w - 1, int(x1)))
    x2 = max(0, min(w - 1, int(x2)))
    y1 = max(0, min(h - 1, int(y1)))
    y2 = max(0, min(h - 1, int(y2)))
    if x2 <= x1 or y2 <= y1:
        return None
    crop = img[y1:y2, x1:x2].copy()
    return crop if crop.size > 0 else None


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", type=str, default="videos/sample.mp4", help="path to input mp4")
    ap.add_argument("--buffer-min", type=int, default=4, help="rolling buffer minutes")
    ap.add_argument("--chunk-sec", type=int, default=10, help="chunk length in seconds")

    ap.add_argument("--car-model", type=str, default="yolov8n.pt", help="YOLO model for vehicles")
    ap.add_argument("--plate-model", type=str, default="", help="path to plate model .pt (optional)")

    ap.add_argument("--car-conf", type=float, default=0.35)
    ap.add_argument("--plate-conf", type=float, default=0.35)

    # If this file isn't present, Ultralytics will still try internal defaults.
    ap.add_argument("--tracker", type=str, default="bytetrack.yaml", help="bytetrack.yaml or botsort.yaml")
    return ap.parse_args()


def main():
    args = parse_args()

    print("HELLO FROM MAIN.PY", flush=True)
    import sys
    print("Python:", sys.version, flush=True)
    print("Using video:", args.video, flush=True)

    # Output dirs
    chunks_dir = "data/raw_buffer/chunks"
    plates_dir = "data/raw_buffer/plates"
    logs_dir = "data/raw_buffer/logs"
    os.makedirs(chunks_dir, exist_ok=True)
    os.makedirs(plates_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)

    # Open video
    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        raise RuntimeError(f"❌ Video not opened: {args.video}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print("Video opened:", cap.isOpened(), flush=True)
    print("FPS:", fps, flush=True)

    # Rolling buffer writer
    buffer_writer = RollingBufferWriter(
        out_dir=chunks_dir,
        fps=fps,
        frame_size=(W, H),
        chunk_seconds=args.chunk_sec,
        keep_minutes=args.buffer_min,
    )

    # Models
    car_model = YOLO(args.car_model)

    plate_model = None
    if args.plate_model and os.path.exists(args.plate_model):
        plate_model = YOLO(args.plate_model)
        print("✅ Plate model loaded:", args.plate_model, flush=True)
    else:
        print("⚠️ Plate model not provided/found. Plate detection will be skipped.", flush=True)

    # COCO vehicle classes: car(2), motorcycle(3), bus(5), truck(7)
    vehicle_classes = [2, 3, 5, 7]

    # Tracking + counts
    seen_vehicle_ids = set()
    log_rows = []

    # Plate save throttling: avoid saving 1000 similar crops
    last_saved_plate_ts = {}  # assoc_id -> last time saved
    MIN_SAVE_GAP_SEC = 2.0

    frame_idx = 0
    t0 = time.time()
    last_plate_debug = 0.0

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        frame_idx += 1

        if frame_idx == 1:
            print("[debug] first frame reached, writing to buffer...", flush=True)


        # 1) store raw buffer
        buffer_writer.write(frame)

        # 2) detect + track vehicles
        try:
            results = car_model.track(
                source=frame,
                conf=args.car_conf,
                classes=vehicle_classes,
                tracker=args.tracker,
                persist=True,
                verbose=False,
            )[0]
        except Exception as e:
            # If tracker yaml causes issues, fallback to predict (no tracking)
            print(f"⚠️ track() failed ({e}). Falling back to predict() (no tracking).", flush=True)
            results = car_model.predict(
                source=frame,
                conf=args.car_conf,
                classes=vehicle_classes,
                verbose=False,
            )[0]

        vehicle_boxes = []
        cars_in_frame = 0

        if results.boxes is not None and results.boxes.xyxy is not None:
            xyxy = results.boxes.xyxy.cpu().numpy()

            ids = None
            if getattr(results.boxes, "id", None) is not None:
                try:
                    ids = results.boxes.id.cpu().numpy().astype(int)
                except Exception:
                    ids = None

            for i in range(len(xyxy)):
                x1, y1, x2, y2 = xyxy[i]
                tid = int(ids[i]) if ids is not None else -1
                vehicle_boxes.append((x1, y1, x2, y2, tid))
                cars_in_frame += 1
                if tid != -1:
                    seen_vehicle_ids.add(tid)

        # 3) plate detection + crop (optional)
        if plate_model is not None:
            pres = plate_model.predict(frame, conf=args.plate_conf, verbose=False)[0]

            if pres.boxes is None or pres.boxes.xyxy is None or len(pres.boxes) == 0:
                if time.time() - last_plate_debug > 2:
                    print("[debug] no plates detected in recent frames", flush=True)
                    last_plate_debug = time.time()
            else:
                pxyxy = pres.boxes.xyxy.cpu().numpy()

        # ✅ ADD THIS LINE
                print(f"[plate-debug] detected {len(pxyxy)} plates", flush=True)

                pconf = pres.boxes.conf.cpu().numpy() if pres.boxes.conf is not None else None

                for j in range(len(pxyxy)):
                    px1, py1, px2, py2 = pxyxy[j]
                    confv = float(pconf[j]) if pconf is not None else None

                    crop = safe_crop(frame, px1, py1, px2, py2)
                    if crop is None:
                        continue
            


                    # associate plate -> vehicle if plate center inside a vehicle box
                    cx = (px1 + px2) / 2
                    cy = (py1 + py2) / 2
                    assoc_id = -1
                    for (x1, y1, x2, y2, tid) in vehicle_boxes:
                        if x1 <= cx <= x2 and y1 <= cy <= y2:
                            assoc_id = tid
                            break

                    ts = time.time()

                    # throttle saves per vehicle id
                    if assoc_id != -1:
                        last_t = last_saved_plate_ts.get(assoc_id, 0.0)
                        if (ts - last_t) < MIN_SAVE_GAP_SEC:
                            continue
                        last_saved_plate_ts[assoc_id] = ts

                    stamp = datetime.fromtimestamp(ts).strftime("%Y%m%d_%H%M%S_%f")
                    out_name = f"plate_{stamp}_vid{assoc_id}.jpg"
                    out_path = os.path.join(plates_dir, out_name)

                    ok_write = cv2.imwrite(out_path, crop)
                    if not ok_write:
                        print(f"⚠️ Failed to write plate crop: {out_path}", flush=True)
                        continue

                    log_rows.append(
                        {
                            "timestamp": datetime.fromtimestamp(ts).isoformat(),
                            "frame": frame_idx,
                            "plate_path": out_path,
                            "plate_conf": confv,
                            "associated_vehicle_id": assoc_id,
                            "vehicles_in_frame": cars_in_frame,
                            "unique_vehicles_seen": len(seen_vehicle_ids),
                        }
                    )

        # status print every ~2 seconds
        if frame_idx % max(1, int(fps * 2)) == 0:
            elapsed = time.time() - t0
            print(
                f"[t={elapsed:0.1f}s] vehicles_in_frame={cars_in_frame} unique_total={len(seen_vehicle_ids)}",
                flush=True,
            )

    cap.release()
    buffer_writer.close()

    # Save log
    csv_path = os.path.join(logs_dir, "plate_log.csv")
    pd.DataFrame(log_rows).to_csv(csv_path, index=False)

    print("\n✅ DONE", flush=True)
    print("Frames actually read:", frame_idx, flush=True)
    print("Chunks:", chunks_dir, flush=True)
    print("Plates:", plates_dir, flush=True)
    print("Log:", csv_path, flush=True)


if __name__ == "__main__":
    main()




