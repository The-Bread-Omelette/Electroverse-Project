from Crypto.Cipher import AES

with open("encrypted_video.bin", "rb") as f:
    nonce = f.read(16)
    tag = f.read(16)
    ciphertext = f.read()

# PASTE THE KEY YOU SAVED
key = b'\xb5\x8c\x9f\x01\xa6#\x0eh\xe6\xd4\x94\xbde\x01\xdd\x85\xc5|\x1a5\xfat\xb2F\xad\xc8\xb88[yN\x06'

cipher = AES.new(key, AES.MODE_EAX, nonce=nonce)
video_data = cipher.decrypt_and_verify(ciphertext, tag)

with open("decrypted_output.mp4", "wb") as f:
    f.write(video_data)

print("Decryption successful")