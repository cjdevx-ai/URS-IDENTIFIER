import os
import time
import subprocess
import requests
import cv2
import numpy as np
import pandas as pd
import sys
import json
from datetime import datetime

# --- CONFIGURATION ---
# ESP32 Settings
ESP_SSID = "ESP32-Camera-Connect"
ESP_PASSWORD = "password123"
ESP_IP = "192.168.4.1"

# Home/Data Network Settings (optional)
HOME_SSID = "ZTE_DEE446"  
HOME_PASSWORD = "Your_Home_WiFi_Password"

# File Paths
SAVE_FOLDER = "captured_images_rpi"
RESULTS_FOLDER = "analysis_results_rpi"
LOG_FILE = "pipeline_log.txt"

# Pipeline Settings
INTERVAL_MINUTES = 0.5  # How often to run the full cycle
CAPTURE_TIMEOUT = 15  # Seconds to wait for image capture

# Debugging
DEBUG_SKIP_WIFI = False  # Set to True to skip WiFi checks and attempt capture directly

# Urine Strip Parameters (aligned with app.py/bbx.txt)
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

REFERENCE_DATA = {
    "Urobilinogen": {"Normal/3.3": (240, 200, 185), "16": (235, 175, 160), "33 (+)": (218, 140, 130), "66 (++)": (200, 110, 105), "131 (+++)": (175, 75, 80)},
    "Bilirubin": {"Neg": (232, 205, 185), "Small/17": (215, 175, 145), "Moderate/50": (195, 148, 115), "Large/100": (168, 115, 85)},
    "Ketone": {"Neg": (230, 200, 195), "Trace/0.5": (215, 175, 178), "Small/1.5": (195, 148, 165), "Moderate/4.0": (168, 110, 148), "8.0": (148, 70, 120), "Large/16": (120, 40, 90)},
    "Creatinine": {"0.9": (228, 218, 195), "4.4": (210, 200, 172), "8.8": (188, 178, 148), "17.7": (160, 150, 120), "26.5": (130, 120, 92)},
    "Blood": {"Neg": (225, 185, 100), "Non-hemolyzed Trace/10": (195, 165, 110), "Hemolyzed Trace/10": (168, 148, 118), "Small/25": (140, 128, 120), "Moderate/80": (95, 110, 85), "Large/200": (55, 75, 50)},
    "Protein": {"Neg": (235, 235, 175), "Trace (±)": (215, 225, 150), "0.3 (+)": (175, 205, 120), "1.0 (++)": (135, 185, 100), "3.0 (+++)": (100, 158, 80), ">20.0 (++++)": (65, 125, 55)},
    "Micro Albumin": {"10": (195, 228, 225), "30": (165, 210, 210), "80": (130, 190, 195), "150": (95, 165, 175)},
    "Nitrite": {"Neg": (238, 220, 215), "Positive (any uniform pink)": (225, 175, 185)},
    "Leukocytes": {"Neg": (235, 220, 205), "Trace/15": (220, 200, 185), "Small/70": (198, 172, 168), "Moderate/125": (175, 140, 158), "Large/500": (148, 105, 140)},
    "Glucose": {"Neg": (175, 210, 175), "Trace/5": (145, 195, 148), "15 (+)": (115, 175, 120), "30 (++)": (85, 150, 90), "60 (+++)": (165, 105, 45), "110 (++++)": (130, 65, 30)},
    "Specific Gravity": {"1.000": (55, 138, 95), "1.005": (42, 115, 80), "1.010": (65, 128, 58), "1.015": (105, 140, 42), "1.020": (148, 152, 38), "1.025": (188, 158, 42), "1.030": (205, 148, 38)},
    "pH": {"5.0": (215, 175, 68), "6.0": (195, 185, 68), "6.5": (172, 188, 65), "7.0": (148, 185, 62), "7.5": (115, 165, 62), "8.0": (85, 140, 65), "8.5": (55, 105, 110)},
    "Ascorbate": {"0": (55, 105, 118), "0.6": (95, 155, 100), "1.4": (145, 185, 80), "2.8": (185, 205, 78), "5.0": (215, 218, 115)},
    "Calcium": {"≤1.0": (235, 228, 205), "2.5": (218, 215, 190), "5.0": (200, 195, 185), "7.5": (185, 178, 195), "≥10": (168, 158, 205)}
}

# UART Settings (Future Trigger)
UART_PORT = "COM3"  
UART_BAUD = 115200
USE_UART_TRIGGER = False 

# --- HELPERS ---

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_msg = f"[{timestamp}] {message}"
    print(formatted_msg)
    with open(LOG_FILE, "a") as f:
        f.write(formatted_msg + "\n")

def is_connected_to(ssid):
    """Check if the system is currently connected to the given SSID."""
    try:
        if sys.platform == "win32":
            verify_cmd = ["netsh", "wlan", "show", "interfaces"]
            verify_result = subprocess.run(verify_cmd, capture_output=True, text=True)
            return f"SSID                   : {ssid}" in verify_result.stdout
        else:
            # 1. Try iwgetid (most reliable for simple SSID check)
            try:
                res = subprocess.run(["iwgetid", "-r"], capture_output=True, text=True)
                if res.returncode == 0 and res.stdout.strip() == ssid:
                    return True
            except Exception:
                pass

            # 2. Try nmcli
            try:
                cmd = ["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0 and f"yes:{ssid}" in result.stdout:
                    return True
            except Exception:
                pass
            
            # 3. Try checking IP route (if connected to ESP32 AP)
            if ssid == ESP_SSID:
                try:
                    route_res = subprocess.run(["ip", "addr", "show", "wlan0"], capture_output=True, text=True)
                    # Check if we have an IP in the 192.168.4.x range
                    if "192.168.4." in route_res.stdout:
                        return True
                except Exception:
                    pass

            return False
    except Exception as e:
        log(f"Error in is_connected_to: {e}")
        return False

def switch_wifi(ssid, password=None):
    """Switch Wi-Fi with aggressive logging for RPi debugging."""
    if DEBUG_SKIP_WIFI:
        log(f"DEBUG: Skipping WiFi switch to {ssid}")
        return True

    if is_connected_to(ssid):
        log(f"Already connected to {ssid}")
        return True

    log(f"Attempting to connect to SSID: {ssid}...")
    try:
        if sys.platform == "win32":
            cmd = ["netsh", "wlan", "connect", f"name={ssid}"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                log(f"Connection command sent for {ssid}. Waiting...")
                for _ in range(15):
                    time.sleep(2)
                    if is_connected_to(ssid): return True
                log(f"Timeout waiting for connection to {ssid}")
                return False
            else:
                log(f"Netsh command failed: {result.stderr}")
                return False
        else:
            # Linux: Try nmcli then wpa_cli
            nmcli_available = False
            try:
                # Check if nmcli exists
                subprocess.run(["nmcli", "--version"], capture_output=True, check=True)
                nmcli_available = True
            except (FileNotFoundError, subprocess.CalledProcessError):
                pass

            if nmcli_available:
                try:
                    if password:
                        cmd = ["nmcli", "dev", "wifi", "connect", ssid, "password", password]
                    else:
                        cmd = ["nmcli", "dev", "wifi", "connect", ssid]
                    
                    log(f"Running nmcli: {' '.join(cmd)}")
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
                    if result.returncode == 0:
                        log(f"Successfully connected to {ssid} via nmcli")
                        return True
                    else:
                        log(f"nmcli failed to connect: {result.stderr or result.stdout}")
                        # Fall through to wpa_cli if nmcli fails
                except Exception as e:
                    log(f"nmcli error: {e}")

            # Fallback to wpa_cli
            log(f"Attempting wpa_cli fallback for {ssid}...")
            try:
                # Check if ssid is in wpa_cli list networks
                list_res = subprocess.run(["wpa_cli", "list_networks"], capture_output=True, text=True)
                net_id = None
                for line in list_res.stdout.splitlines():
                    if ssid in line:
                        parts = line.split()
                        if len(parts) > 1 and parts[1] == ssid:
                            net_id = parts[0]
                            break
                
                if net_id:
                    log(f"Found {ssid} with network ID {net_id}. Selecting...")
                    subprocess.run(["wpa_cli", "select_network", net_id], capture_output=True)
                else:
                    log(f"SSID {ssid} not found in wpa_supplicant configuration. Attempting direct select (may fail)...")
                    subprocess.run(["wpa_cli", "select_network", ssid], capture_output=True)

                for _ in range(15):
                    time.sleep(2)
                    if is_connected_to(ssid): 
                        log(f"Successfully connected to {ssid} via wpa_cli")
                        return True
                
                log(f"wpa_cli fallback failed to connect to {ssid}. Tip: Ensure network is configured in /etc/wpa_supplicant/wpa_supplicant.conf")
                return False
            except Exception as e:
                log(f"wpa_cli error: {e}")
                return False


    except Exception as e:
        log(f"Error during WiFi switch: {e}")
        return False


def get_closest_match(r, g, b, parameter_name):
    if parameter_name not in REFERENCE_DATA:
        return "N/A"
    refs = REFERENCE_DATA[parameter_name]
    min_dist = float('inf')
    best_match = "Unknown"
    for label, ref_rgb in refs.items():
        dist = np.sqrt((r - ref_rgb[0])**2 + (g - ref_rgb[1])**2 + (b - ref_rgb[2])**2)
        if dist < min_dist:
            min_dist = dist
            best_match = label
    return best_match

def process_image(img_path, timestamp):
    img = cv2.imread(img_path)
    if img is None:
        log(f"Error: Could not load image {img_path}")
        return None

    results = []
    debug_img = img.copy()
    
    for i, (name, coord) in enumerate(zip(PARAMETERS, ROI_COORDS)):
        x, y, size = coord
        roi = img[y:y+size, x:x+size]
        
        if roi.size > 0:
            avg_color_bgr = cv2.mean(roi)[:3]
            r, g, b = int(avg_color_bgr[2]), int(avg_color_bgr[1]), int(avg_color_bgr[0])
            match = get_closest_match(r, g, b, name)
            results.append({"Parameter": name, "R": r, "G": g, "B": b, "Match": match})
            cv2.rectangle(debug_img, (x, y), (x+size, y+size), (0, 255, 0), 2)
        else:
            results.append({"Parameter": name, "R": None, "G": None, "B": None, "Match": "ROI Error"})

    df = pd.DataFrame(results)
    csv_filename = os.path.join(RESULTS_FOLDER, f"results_{timestamp}.csv")
    df.to_csv(csv_filename, index=False)
    
    debug_filename = os.path.join(RESULTS_FOLDER, f"debug_{timestamp}.jpg")
    cv2.imwrite(debug_filename, debug_img)
    
    log(f"Processing complete. Results saved to {csv_filename}")
    return results

def release_results(results):
    log("NOTICE<\"Final Results Release\">")
    filtered = [{"Parameter": r["Parameter"], "Match": r["Match"]} for r in results]
    print(json.dumps(filtered, indent=4, ensure_ascii=False))
    log("NOTICE<\"Results released successfully\">")

def wait_for_uart_trigger():
    if not USE_UART_TRIGGER: return True
    log(f"NOTICE<\"Waiting for UART trigger on {UART_PORT}...\">")
    return True 

# --- MAIN LOOP ---

def run_pipeline():
    if not os.path.exists(SAVE_FOLDER): os.makedirs(SAVE_FOLDER)
    if not os.path.exists(RESULTS_FOLDER): os.makedirs(RESULTS_FOLDER)

    while True:
        if not wait_for_uart_trigger():
            time.sleep(10)
            continue

        log("NOTICE<\"Starting new pipeline cycle\">")
        
        if switch_wifi(ESP_SSID, ESP_PASSWORD):
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = os.path.join(SAVE_FOLDER, f"img_{timestamp}.jpg")
            
            try:
                log(f"NOTICE<\"Requesting capture from http://{ESP_IP}/capture\">")
                response = requests.get(f"http://{ESP_IP}/capture", timeout=CAPTURE_TIMEOUT)
                if response.status_code == 200:
                    with open(filename, "wb") as f:
                        f.write(response.content)
                    log(f"NOTICE<\"Image saved: {filename}\">")
                    
                    results = process_image(filename, timestamp)
                    
                    if HOME_SSID not in ["Your_Home_WiFi_SSID", ""]:
                        if switch_wifi(HOME_SSID, HOME_PASSWORD):
                            if results: release_results(results)
                    else:
                        if results: release_results(results)
                else:
                    log(f"NOTICE<\"Capture failed. HTTP Status: {response.status_code}\">")
            except Exception as e:
                log(f"NOTICE<\"Capture error: {e}\">")
        
        log(f"NOTICE<\"Cycle Complete. Waiting {INTERVAL_MINUTES} minutes...\">")
        time.sleep(INTERVAL_MINUTES * 60)

if __name__ == "__main__":
    try:
        run_pipeline()
    except KeyboardInterrupt:
        log("Pipeline stopped by user.")
