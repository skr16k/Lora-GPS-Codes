#include <TinyGPS++.h>
#include <SoftwareSerial.h>
#include <SPI.h>
#include <LoRa.h>

// GPS pins for Wemos D1 Mini
#define GPS_RX D1   // GPS TX → D5
#define GPS_TX D3   // GPS RX → D6

// LoRa pins
#define LORA_SCK  D5
#define LORA_MISO D6
#define LORA_MOSI D7
#define LORA_CS   D8
#define LORA_RST  D0
#define LORA_DIO0 D2

#define LORA_FREQ 433E6   // or 868E6 depending on your module

TinyGPSPlus gps;
SoftwareSerial gpsSerial(GPS_RX, GPS_TX);

// smartDelay keeps reading GPS while waiting
void smartDelay(unsigned long ms) {
  unsigned long start = millis();
  do {
    while (gpsSerial.available()) {
      gps.encode(gpsSerial.read());
    }
  } while (millis() - start < ms);
}

void setup() {
  Serial.begin(9600);
  gpsSerial.begin(9600);

  Serial.println("GPS + LoRa Sender Starting...");

  // LoRa initialization
  LoRa.setPins(LORA_CS, LORA_RST, LORA_DIO0);

  if (!LoRa.begin(LORA_FREQ)) {
    Serial.println("LoRa initialization failed!");
    while (1);
  }

  Serial.println("LoRa OK!");
}

void loop() {
  smartDelay(1000);

  if (gps.location.isValid()) {
    double lat = gps.location.lat();
    double lng = gps.location.lng();
    int sats = gps.satellites.value();

    // Print GPS to Serial
    Serial.print("Lat: ");
    Serial.println(lat, 6);
    Serial.print("Lng: ");
    Serial.println(lng, 6);
    Serial.print("Satellites: ");
    Serial.println(sats);
    Serial.println("-----------------");

    // Prepare LoRa packet
    String packet = String(lat, 6) + "," + String(lng, 6);

    // Send LoRa packet
    LoRa.beginPacket();
    LoRa.print(packet);
    LoRa.endPacket();

    Serial.print("LoRa Sent: ");
    Serial.println(packet);
  }
  else {
    Serial.println("Waiting for GPS fix...");
  }

  smartDelay(2000);
}
