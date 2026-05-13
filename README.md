## WiFi Mode (Original)
Flash the example code, then open the serial monitor (baud rate: 115200). Follow the prompts to enter your WiFi SSID and password to connect to WiFi. After a successful connection, access the IP address displayed in the serial monitor via a web browser to access the monitoring backend. Click the "Start Stream" button to obtain the image stream.

## Wired Image Transfer Mode (New)
This mode allows you to transfer images directly over the USB/Serial cable without requiring WiFi.

### 1. ESP32 Setup
1. Open `source code/5_3/5_3.ino`.
2. Ensure the baud rate is set to `921600` in `Serial.begin()`.
3. Upload the code to your ESP32.

### 2. Python Setup
1. Install dependencies: `pip install -r requirements.txt`.
2. Open `grab_photos.py` and update the `SERIAL_PORT` (e.g., `COM3` on Windows or `/dev/ttyUSB0` on Linux).
3. Ensure `BAUD_RATE` matches the ESP32 (default `921600`).

### 3. Usage
Run the Python script:
```bash
python grab_photos.py
```
The script will send a `CAPTURE` command every 5 seconds (configurable) and save the resulting images to the `captured_images` folder.

## Wireless AP Mode (New)
This mode allows you to transfer images wirelessly by connecting your PC directly to the ESP32's own WiFi network. No router is needed.

### 1. ESP32 Setup
1. Open `source code/5_3/5_3_ap.ino`.
2. Upload the code to your ESP32.

### 2. PC Setup
1. On your PC, search for WiFi networks and connect to:
   - **SSID:** `ESP32-Camera-Connect`
   - **Password:** `password123`

### 3. Usage
Run the dedicated AP Python script:
```bash
python grab_photos_ap.py
```
Images will be saved to the `captured_images_ap` folder.

## Streamlit Analysis Dashboard (New)
A unified GUI for both Wired and Wireless modes that provides real-time image capture, ROI visualization, and color analysis.

### 1. Setup
1. Install requirements: `pip install -r requirements.txt`.
2. Ensure your ESP32 is flashed with the appropriate code (`5_3_usb_c.ino` or `5_3_ap.ino`).

### 2. Launching the GUI
Run the following command in your terminal:
```bash
streamlit run app.py
```

### 3. Features
- **Mode Selection:** Switch between USB-C (Serial) and Wireless (AP) in the sidebar.
- **Real-time Analysis:** Click "Capture & Analyze" to take a photo.
- **ROI Visualization:** The captured image will show green bounding boxes around the 14 test pads.
- **Detailed Results:** A side panel displays each parameter with its average RGB values and a visual color swatch.

## Raspberry Pi Zero W Setup Guide
Since the RPi Zero W uses an ARMv6 architecture and has limited RAM (512MB), follow this guide for a stable setup.

### 1. Expand Filesystem
Ensure your SD card's full capacity is available:
1. Run `sudo raspi-config`.
2. Go to **6 Advanced Options** > **A1 Expand Filesystem**.
3. Finish and **Reboot**.

### 2. Install System Dependencies
Install pre-compiled libraries to avoid long compilation times:
```bash
sudo apt update
sudo apt install -y python3-opencv python3-numpy python3-pandas python3-requests python3-pil libopenblas-dev
```

### 3. Virtual Environment Setup
Create a virtual environment that uses the system-installed packages:
```bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
```

### 4. Project Installation
Install the remaining requirements using the `--no-cache-dir` flag to save memory:
```bash
pip install -r requirements.txt --no-cache-dir
```

### 5. WiFi Configuration (Automatic Switching)
For the `automated_pipeline.py` to switch between ESP32 and Home WiFi on RPi OS Lite, add your networks to `/etc/wpa_supplicant/wpa_supplicant.conf`:
```bash
network={
    ssid="Your_Home_SSID"
    psk="your_password"
    id_str="home"
}
network={
    ssid="ESP32-Camera-Connect"
    psk="password123"
    id_str="esp32"
}
```
