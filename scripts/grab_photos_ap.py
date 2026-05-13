import requests
import time
import os
import cv2
import numpy as np

# --- CONFIGURATION ---
# Default IP for ESP32 in Access Point mode
ESP_IP = "192.168.4.1"  
SAVE_FOLDER = "captured_images_ap"
DEBUG_FOLDER = "processed_results"
INTERVAL = 15             # Seconds between photos

# Urine Test Strip ROIs (from bbx.txt)
PARAMETERS = [
    "Urobilinogen", "Bilirubin", "Ketone", "Creatinine", "Blood", 
    "Protein", "Micro Albumin", "Nitrite", "Leukocytes", "Glucose", 
    "Specific Gravity", "pH", "Ascorbate", "Calcium"
]

ROI_COORDS = [
    (15, 320, 15), (65, 320, 15), (125, 320, 15), (195, 320, 15), 
    (275, 320, 15), (365, 320, 15), (475, 320, 15), (590, 320, 15), 
    (715, 320, 15), (835, 320, 15), (945, 320, 15), (1045, 320, 15), 
    (1130, 320, 15), (1210, 320, 15)
]
# ---------------------

if not os.path.exists(SAVE_FOLDER):
    os.makedirs(SAVE_FOLDER)
if not os.path.exists(DEBUG_FOLDER):
    os.makedirs(DEBUG_FOLDER)

def process_image(img_path):
    img = cv2.imread(img_path)
    if img is None:
        print(f"Error: Could not load image {img_path}")
        return

    # Create a copy for visual debug
    debug_img = img.copy()
    
    print(f"\n--- Analysis Results: {os.path.basename(img_path)} ---")
    print(f"{'Parameter':<20} | {'R':<4} | {'G':<4} | {'B':<4}")
    print("-" * 40)

    for i, (name, coord) in enumerate(zip(PARAMETERS, ROI_COORDS)):
        x, y, size = coord
        
        # Extract ROI
        roi = img[y:y+size, x:x+size]
        
        if roi.size > 0:
            # OpenCV uses BGR, we convert to RGB for printing
            avg_color_bgr = cv2.mean(roi)[:3]
            r, g, b = int(avg_color_bgr[2]), int(avg_color_bgr[1]), int(avg_color_bgr[0])
            print(f"{name:<20} | {r:<4} | {g:<4} | {b:<4}")
            
            # Draw on debug image
            cv2.rectangle(debug_img, (x, y), (x+size, y+size), (0, 255, 0), 2)
            cv2.putText(debug_img, str(i+1), (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        else:
            print(f"{name:<20} | ROI Error")

    # Save debug image
    debug_filename = os.path.join(DEBUG_FOLDER, "debug_" + os.path.basename(img_path))
    cv2.imwrite(debug_filename, debug_img)
    print(f"Analysis complete. Debug image saved to: {debug_filename}\n")

print("--- ESP32 Wireless AP Mode with Urine Strip Pipeline ---")
print(f"1. Connect your PC to WiFi SSID: 'ESP32-Camera-Connect'")
print(f"2. Password: 'password123'")
print(f"3. Automation will save to '{SAVE_FOLDER}' every {INTERVAL}s...")
print("Press Ctrl+C to stop.")

try:
    while True:
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = os.path.join(SAVE_FOLDER, f"img_ap_{timestamp}.jpg")
        
        try:
            # Request the image from the ESP32
            url = f"http://{ESP_IP}/capture"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                with open(filename, "wb") as f:
                    f.write(response.content)
                print(f"[{time.strftime('%H:%M:%S')}] Saved: {filename}")
                
                # Run the processing pipeline
                process_image(filename)
            else:
                print(f"[{time.strftime('%H:%M:%S')}] Failed to capture. HTTP Error: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"[{time.strftime('%H:%M:%S')}] Connection error: {e}")
            print("Tip: Ensure you are connected to the ESP32's WiFi network.")
        
        time.sleep(INTERVAL)

except KeyboardInterrupt:
    print("\nAutomation stopped by user.")
except Exception as e:
    print(f"Unexpected error: {e}")
