from Crypto.Random import get_random_bytes
import os

path = r"E:\Clubs and other things\electroverse\encryption\configs"


print("Target path:", path)
print("Path exists before:", os.path.exists(path))


os.makedirs(path, exist_ok=True)

print("Path exists after:", os.path.exists(path))


key = get_random_bytes(32)
print("Key length:", len(key))

file_path = os.path.join(path, "secret.key")
print("Saving to:", file_path)

with open(file_path, "wb") as f:
    f.write(key)

print("Done.")
