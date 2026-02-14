import threading
import time

from src.record import record 
from src.encryption.encryption import encryption
from src.plates_detect.plates_detect import detetct_plates
from src.server.app import server

stop_event = threading.Event()


def cv_thread():
    time.sleep(0)  
    
    while not stop_event.is_set():
        run_cv()
        time.sleep(5)  
        # interval between runs and me soch raha ki har me yaa to 5 ,5 sec ka rakhu run time 

def encryption_thread():
    time.sleep(2)
    while not stop_event.is_set():
        encrypt_worker()
        time.sleep(6)


def decryption_thread():
    time.sleep(4)  
    while not stop_event.is_set():
        decrypt_worker()
        time.sleep(7)


def cleanup_thread():
    time.sleep(6)  
    while not stop_event.is_set():
        cleanup_worker()
        time.sleep(10)

threads = [
    threading.Thread(target=cv_thread),
    threading.Thread(target=encryption_thread),
    threading.Thread(target=decryption_thread),
    threading.Thread(target=cleanup_thread)
]

for t in threads:
    t.start()

try:
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("\nStopping system safely...")
    stop_event.set()

    for t in threads:
        t.join()

    print("System stopped successfully.")