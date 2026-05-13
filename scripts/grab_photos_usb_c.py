import serial
import time
import os

# --- CONFIGURATION ---
# Replace with your ESP32's Serial Port (e.g., "COM3" on Windows or "/dev/ttyUSB0" on Linux)
SERIAL_PORT = "COM10"  
BAUD_RATE = 921600   # Must match the baud rate in 5_3.ino
SAVE_FOLDER = "captured_images"
INTERVAL = 5         # Seconds between photos
# ---------------------

if not os.path.exists(SAVE_FOLDER):
    os.makedirs(SAVE_FOLDER)

print(f"Starting automation. Saving to '{SAVE_FOLDER}' every {INTERVAL}s...")
print(f"Target ESP32 Serial Port: {SERIAL_PORT} at {BAUD_RATE} baud")
print("Press Ctrl+C to stop.")

try:
    # Initialize serial connection
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=10)
    time.sleep(2)  # Wait for ESP32 to reboot after serial connection
    ser.flushInput()

    while True:
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = os.path.join(SAVE_FOLDER, f"img_{timestamp}.jpg")
        
        try:
            # Request the image from the ESP32
            ser.write(b"CAPTURE\n")
            
            # Wait for IMG_START header
            line = ""
            start_time = time.time()
            while "IMG_START:" not in line:
                if ser.in_waiting > 0:
                    line = ser.readline().decode(errors='ignore').strip()
                if time.time() - start_time > 5: # 5 second timeout for header
                    break
            
            if "IMG_START:" in line:
                try:
                    size = int(line.split(":")[1])
                    print(f"[{time.strftime('%H:%M:%S')}] Receiving {size} bytes...")
                    
                    img_data = ser.read(size)
                    
                    if len(img_data) == size:
                        with open(filename, "wb") as f:
                            f.write(img_data)
                        print(f"[{time.strftime('%H:%M:%S')}] Saved: {filename}")
                        
                        # Consume the IMG_END footer
                        footer = ser.readline().decode(errors='ignore').strip()
                    else:
                        print(f"[{time.strftime('%H:%M:%S')}] Timeout or incomplete data. Received {len(img_data)}/{size}")
                except (ValueError, IndexError) as e:
                    print(f"[{time.strftime('%H:%M:%S')}] Malformed header: {line}")
            else:
                print(f"[{time.strftime('%H:%M:%S')}] Failed to get IMG_START header. Line received: {line}")
                
        except serial.SerialException as e:
            print(f"[{time.strftime('%H:%M:%S')}] Serial error: {e}")
            # Try to reconnect
            ser.close()
            time.sleep(1)
            ser.open()
        
        time.sleep(INTERVAL)

except KeyboardInterrupt:
    print("\nAutomation stopped by user.")
    if 'ser' in locals() and ser.is_open:
        ser.close()
except Exception as e:
    print(f"Unexpected error: {e}")
    if 'ser' in locals() and ser.is_open:
        ser.close()
