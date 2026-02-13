
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
INPUT_VIDEO = "input.mp4"
ENCRYPTED_FILE = "encrypted_video.bin"

key = get_random_bytes(32)  # AES-256
cipher = AES.new(key, AES.MODE_EAX)

with open(INPUT_VIDEO, "rb") as f:
    video_bytes = f.read()

ciphertext, tag = cipher.encrypt_and_digest(video_bytes)

with open(ENCRYPTED_FILE, "wb") as f:
    f.write(cipher.nonce + tag + ciphertext)

print(" Encryption successful")
print(" SAVE THIS KEY (VERY IMPORTANT):")
print(key)
 