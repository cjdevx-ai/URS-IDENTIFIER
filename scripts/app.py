import streamlit as st
import requests
import serial
import time
import os
import cv2
import numpy as np
import pandas as pd
from PIL import Image

# --- CONFIGURATION ---
SAVE_FOLDER = "captured_images_gui"
DEBUG_FOLDER = "processed_results_gui"
RESULTS_FOLDER = "analysis_csv"
PARAMETERS = [
    "Urobilinogen", "Bilirubin", "Ketone", "Creatinine", "Blood",
    "Protein", "Micro Albumin", "Nitrite", "Leukocytes", "Glucose",
    "Specific Gravity", "pH", "Ascorbate", "Calcium"
]
ROI_COORDS = [
    (1210, 320, 15), (1130, 320, 15), (1045, 320, 15), (945, 320, 15), 
    (835, 320, 15), (715, 320, 15), (590, 320, 15), (475, 320, 15), 
    (365, 320, 15), (275, 320, 15), (195, 320, 15), (125, 320, 15), 
    (65, 320, 15), (15, 320, 15)
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

# --- PROCESSING LOGIC ---
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

def analyze_image(img_bgr):
    results = []
    debug_img = img_bgr.copy()
    
    for i, (name, coord) in enumerate(zip(PARAMETERS, ROI_COORDS)):
        x, y, size = coord
        roi = img_bgr[y:y+size, x:x+size]
        
        if roi.size > 0:
            avg_color_bgr = cv2.mean(roi)[:3]
            r, g, b = int(avg_color_bgr[2]), int(avg_color_bgr[1]), int(avg_color_bgr[0])
            
            # Match color
            match = get_closest_match(r, g, b, name)
            results.append({"name": name, "r": r, "g": g, "b": b, "match": match})
            
            # Draw for debug
            cv2.rectangle(debug_img, (x, y), (x+size, y+size), (0, 255, 0), 2)
            cv2.putText(debug_img, f"{i+1}:{match}", (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        else:
            results.append({"name": name, "r": None, "g": None, "b": None, "match": "Error"})
            
    return results, debug_img

# --- CAPTURE METHODS ---
def capture_wired(port, baud):
    try:
        ser = serial.Serial(port, baud, timeout=5)
        time.sleep(1)
        ser.flushInput()
        ser.write(b"CAPTURE\n")
        
        line = ""
        start_time = time.time()
        while "IMG_START:" not in line:
            if ser.in_waiting > 0:
                line = ser.readline().decode(errors='ignore').strip()
            if time.time() - start_time > 5:
                return None, "Timeout waiting for header"
        
        size = int(line.split(":")[1])
        img_data = ser.read(size)
        ser.close()
        
        if len(img_data) == size:
            nparr = np.frombuffer(img_data, np.uint8)
            return cv2.imdecode(nparr, cv2.IMREAD_COLOR), None
        return None, "Incomplete image data"
    except Exception as e:
        return None, str(e)

def capture_wireless(ip):
    try:
        url = f"http://{ip}/capture"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            nparr = np.frombuffer(response.content, np.uint8)
            return cv2.imdecode(nparr, cv2.IMREAD_COLOR), None
        return None, f"HTTP Error: {response.status_code}"
    except Exception as e:
        return None, str(e)

# --- STREAMLIT UI ---
st.set_page_config(page_title="Urine Strip Analyzer", layout="wide")

st.title("🧪 Urine Test Strip Analyzer")

# Initialize session state for persistent data
if 'last_capture' not in st.session_state:
    st.session_state.last_capture = None

st.sidebar.header("Connection Settings")
mode = st.sidebar.radio("Connection Mode", ["Wired (USB-C)", "Wireless (AP)"])

if mode == "Wired (USB-C)":
    port = st.sidebar.text_input("Serial Port", "COM3")
    baud = st.sidebar.number_input("Baud Rate", value=921600)
else:
    ip = st.sidebar.text_input("ESP32 IP", "192.168.4.1")

if st.button("📸 Capture & Analyze", use_container_width=True):
    with st.spinner("Capturing image..."):
        if mode == "Wired (USB-C)":
            img, err = capture_wired(port, baud)
        else:
            img, err = capture_wireless(ip)
            
    if err:
        st.error(f"Capture Failed: {err}")
    elif img is not None:
        ts = time.strftime("%Y%m%d-%H%M%S")
        results, debug_img = analyze_image(img)
        
        # Store in session state for persistence
        st.session_state.last_capture = {
            "ts": ts,
            "raw_img": img,
            "debug_img": debug_img,
            "results": results
        }

if st.session_state.last_capture:
    data = st.session_state.last_capture
    
    # Save Actions
    col_save1, col_save2 = st.columns(2)
    with col_save1:
        if st.button("💾 Save (CSV + Images)", use_container_width=True):
            ts = data["ts"]
            # Save Images
            cv2.imwrite(os.path.join(SAVE_FOLDER, f"raw_{ts}.jpg"), data["raw_img"])
            cv2.imwrite(os.path.join(DEBUG_FOLDER, f"debug_{ts}.jpg"), data["debug_img"])
            # Save CSV
            df = pd.DataFrame(data["results"])
            csv_path = os.path.join(RESULTS_FOLDER, f"results_{ts}.csv")
            df.to_csv(csv_path, index=False)
            st.success(f"Successfully saved locally with ID: {ts}")
            
    with col_save2:
        df = pd.DataFrame(data["results"])
        csv_bytes = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download CSV",
            data=csv_bytes,
            file_name=f"results_{data['ts']}.csv",
            mime="text/csv",
            use_container_width=True
        )

    # Display results in columns
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Analysis Visualization")
        rgb_img = cv2.cvtColor(data["debug_img"], cv2.COLOR_BGR2RGB)
        st.image(rgb_img, use_column_width=True, caption=f"Capture ID: {data['ts']}")
        
    with col2:
        st.subheader("Analysis Results")
        for res in data["results"]:
            with st.container():
                c1, c2 = st.columns([3, 2])
                c1.write(f"**{res['name']}**")
                if res['r'] is not None:
                    color_hex = '#%02x%02x%02x' % (res['r'], res['g'], res['b'])
                    c2.markdown(f'<div style="background-color:{color_hex}; width:20px; height:20px; display:inline-block; border:1px solid #000; margin-right:5px; vertical-align: middle;"></div> **{res["match"]}**', unsafe_allow_html=True)
                    c2.caption(f"RGB: {res['r']},{res['g']},{res['b']}")
                else:
                    c2.write("Error")
                st.divider()
else:
    st.info("Configuration: Select mode and click 'Capture' to begin.")