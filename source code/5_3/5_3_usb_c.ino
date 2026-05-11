#include "esp_camera.h"
#include <WiFi.h>

#define PWDN_GPIO_NUM     -1
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM     5
#define Y9_GPIO_NUM       4
#define Y8_GPIO_NUM       6
#define Y7_GPIO_NUM       7
#define Y6_GPIO_NUM       14
#define Y5_GPIO_NUM       17
#define Y4_GPIO_NUM       21
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM       16
#define VSYNC_GPIO_NUM    1
#define HREF_GPIO_NUM     2
#define PCLK_GPIO_NUM     15
#define SIOD_GPIO_NUM     8
#define SIOC_GPIO_NUM     9

#define LED_GPIO_NUM      47

// ==========================
// MANUAL WIFI CONFIGURATION
// ==========================
const char* ssid = "ZTE_DEE446";
const char* password = "1234567890";

void startCameraServer();
void setupLedFlash(int pin);

void connectToWiFi(const char* ssid, const char* password) {
  WiFi.begin(ssid, password);
  Serial.printf("Connecting to WiFi: %s\n", ssid);
  int retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries < 20) {
    delay(500);
    Serial.print(".");
    retries++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected!");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nFailed to connect to WiFi.");
  }
}

void initWiFi() {
  // Simplified to directly use the hardcoded credentials above
  Serial.println("Using hardcoded WiFi credentials.");
  connectToWiFi(ssid, password);
}

void initCamera(){
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 10000000;       // Lowered from 20MHz to 10MHz for stability
  config.frame_size = FRAMESIZE_UXGA;
  config.pixel_format = PIXFORMAT_JPEG;  // for streaming
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 12;
  config.fb_count = 2;                  // Increased to 2 for better buffering

  // Check PSRAM
  if (psramFound()) {
    Serial.println("PSRAM found and enabled!");
    config.jpeg_quality = 10;
    config.fb_count = 2;
    config.grab_mode = CAMERA_GRAB_LATEST;
  } else {
    Serial.println("PSRAM NOT FOUND! Reducing resolution...");
    config.frame_size = FRAMESIZE_SVGA;
    config.fb_location = CAMERA_FB_IN_DRAM;
  }

  // camera init
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return;
  }

  sensor_t *s = esp_camera_sensor_get();
  
  // AUTO-DETECT CAMERA SENSOR AND APPLY SPECIFIC SETTINGS
  if (s->id.PID == OV3660_PID) {
    Serial.println("Camera Detected: OV3660. Applying settings...");
    s->set_vflip(s, 1);        // flip it back
    s->set_brightness(s, 1);   // up the brightness just a bit
    s->set_saturation(s, -2);  // lower the saturation
  } 
  else if (s->id.PID == OV5640_PID) {
    Serial.println("Camera Detected: OV5640. Applying settings...");
    s->set_vflip(s, 1);   // 0 = straight, 1 = flipped vertically
    s->set_hmirror(s, 0); // 0 = straight, 1 = mirrored horizontally
  } 
  else {
    Serial.printf("Camera Detected: Unknown PID (0x%x). Using default settings.\n", s->id.PID);
  }

  // drop down frame size for higher initial frame rate
  if (config.pixel_format == PIXFORMAT_JPEG) {
    s->set_framesize(s, FRAMESIZE_HD); // Set to 720p
  }

  // Set exposure level to -4
  s->set_ae_level(s, -4);
  Serial.println("Exposure level set to -4");
}

void setup() {
  Serial.begin(921600); // Increased baud rate for faster wired transfer
  Serial.setDebugOutput(false); // Disable debug output to avoid interference with binary data
  delay(5000);
  
  Serial.println();
  Serial.println("================================");
  Serial.println("   ESP32 Camera Booting Up...   ");
  Serial.println("================================");
  
  initCamera();
  setupLedFlash(LED_GPIO_NUM);
  // initWiFi(); // Optional: Disable WiFi if only using wired
  // startCameraServer(); // Optional: Disable server if only using wired
  
  Serial.println("READY_FOR_COMMANDS");
}

void captureAndSendSerial() {
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("ERROR: Camera capture failed");
    return;
  }

  // Send header
  Serial.print("IMG_START:");
  Serial.println(fb->len);
  
  // Send data
  Serial.write(fb->buf, fb->len);
  
  // Send footer
  Serial.println("IMG_END");
  
  esp_camera_fb_return(fb);
}

void loop() {
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    if (command == "CAPTURE") {
      captureAndSendSerial();
    }
  }
}