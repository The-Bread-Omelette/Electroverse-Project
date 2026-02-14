import os
import json
import time
import uuid
from datetime import datetime
from Crypto.Cipher import AES


RAW_FOLDER = r"E:\Clubs and other things\electroverse\encryption\data\raw_buffer"
OUT_FOLDER = r"E:\Clubs and other things\electroverse\encryption\data\encrypted"
KEY_PATH = r"E:\Clubs and other things\electroverse\encryption\configs\secret.key"

SCAN_INTERVAL = 10
MAX_CONTAINER_DURATION = 15
CHUNK_DURATION = 3


def load_key():
    with open(KEY_PATH, "rb") as f:
        return f.read()


def wait_for_stable_file(path, wait=3):

    if not os.path.exists(path):
        return False

    size1 = os.path.getsize(path)
    time.sleep(wait)
    size2 = os.path.getsize(path)

    return size1 == size2


def create_new_container():

    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    uid = uuid.uuid4().hex[:8]

    name = f"container_{ts}_{uid}.WattLagGyi"
    path = os.path.join(OUT_FOLDER, name)

    header = {
        "created_at": str(datetime.now()),
        "container_id": uid,
        "encryption": "AES-256-EAX",
        "max_duration_min": MAX_CONTAINER_DURATION
    }

    header_bytes = json.dumps(header).encode()
    header_len = len(header_bytes).to_bytes(4, "big")

    with open(path, "wb") as f:
        f.write(header_len)
        f.write(header_bytes)

    return path


def encrypt_chunk_blob(file_path, key):

    with open(file_path, "rb") as f:
        data = f.read()

    cipher = AES.new(key, AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(data)

    file_size = len(data)

    header = {
        "filename": os.path.basename(file_path),
        "timestamp": str(datetime.now()),
        "file_size": file_size,
        "duration_min": CHUNK_DURATION
    }

    header_bytes = json.dumps(header).encode()
    header_len = len(header_bytes).to_bytes(4, "big")

    return (
        header_len +
        header_bytes +
        cipher.nonce +
        tag +
        ciphertext
    )


def live_encrypt():

    key = load_key()

    current_container = None
    current_duration = 0

    print("Live encryption started...")

    while True:

        files = sorted([
            f for f in os.listdir(RAW_FOLDER)
            if f.endswith(".mp4")
        ])

        for file in files:

            full_path = os.path.join(RAW_FOLDER, file)

            if not wait_for_stable_file(full_path):
                continue

            try:

                if current_container is None:
                    current_container = create_new_container()
                    current_duration = 0

                if current_duration + CHUNK_DURATION > MAX_CONTAINER_DURATION:
                    current_container = create_new_container()
                    current_duration = 0

                blob = encrypt_chunk_blob(full_path, key)

                with open(current_container, "ab") as out:
                    out.write(blob)

                current_duration += CHUNK_DURATION

                os.remove(full_path)

                print(
                    f"Encrypted → {file} "
                    f"→ {os.path.basename(current_container)} "
                    f"({current_duration} min)"
                )

            except Exception as e:
                print(f"Error processing {file}: {e}")

        time.sleep(SCAN_INTERVAL)


if __name__ == "__main__":
    live_encrypt()
