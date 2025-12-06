#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
#include <SPI.h>
#include <LoRa.h>

const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
const char* serverUrl = "http://192.168.1.100:5000/api/gps";

#define SS 15
#define RST 16
#define DIO0 4

WiFiClient wifiClient;

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n🐾 Animal Tracking Receiver");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n✓ WiFi Connected!");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());

  LoRa.setPins(SS, RST, DIO0);
  if (!LoRa.begin(433E6)) {
    Serial.println("✗ LoRa failed!");
    while (1);
  }
  Serial.println("✓ LoRa Ready!\n");
}

void loop() {
  int packetSize = LoRa.parsePacket();
  if (packetSize) {
    String received = "";
    while (LoRa.available()) {
      received += (char)LoRa.read();
    }
    Serial.println("📡 Received: " + received);

    int commaIndex = received.indexOf(',');
    if (commaIndex > 0) {
      float latitude = received.substring(0, commaIndex).toFloat();
      float longitude = received.substring(commaIndex + 1).toFloat();
      int rssi = LoRa.packetRssi();

      if (WiFi.status() == WL_CONNECTED) {
        sendToServer(latitude, longitude, rssi);
      }
    }
  }
  delay(100);
}

void sendToServer(float lat, float lon, int rssi) {
  HTTPClient http;
  String jsonData = "{\"latitude\":" + String(lat, 6) + 
                    ",\"longitude\":" + String(lon, 6) + 
                    ",\"rssi\":" + String(rssi) + 
                    ",\"device_id\":\"collar_001\"}";

  http.begin(wifiClient, serverUrl);
  http.addHeader("Content-Type", "application/json");
  int httpCode = http.POST(jsonData);

  if (httpCode > 0 && httpCode == 200) {
    Serial.println("✓ Data sent!");
  }
  http.end();
}
