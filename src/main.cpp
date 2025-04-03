#include <Arduino.h>
#include "LittleFS.h"
#define FILESYSTEM LittleFS

bool logging_enabled = true;
unsigned long lastLogTime = 0;
const unsigned long logInterval = 10000;

String current_value = "N/A";
String valA = "N/A", valB = "N/A", valC = "N/A", valD = "N/A";

void setup() {
  Serial.begin(115200);
  if (!FILESYSTEM.begin(true)) {
    Serial.println(F("LittleFS Mount Failed"));
    return;
  }
  Serial.println(F("ESP32 Logger Ready"));
}

void loop() {
  // Simulate sensor logging every 10 seconds
  if (logging_enabled && millis() - lastLogTime > logInterval) {
    lastLogTime = millis();
    float temp = random(200, 300) / 10.0;
    float hum = random(400, 600) / 10.0;

    // Create file if missing and add CSV header
    if (!FILESYSTEM.exists("/log.txt")) {
      File headerFile = FILESYSTEM.open("/log.txt", FILE_WRITE);
      if (headerFile) {
        headerFile.println("Temperature,Humidity,Timestamp");
        headerFile.close();
      }
    }

    File file = FILESYSTEM.open("/log.txt", FILE_APPEND);
    if (file) {
      file.printf("%.1f,%.1f,%lu\n", temp, hum, millis() / 1000);
      file.close();
    }
  }

  // Handle serial commands
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    // Value SET
    if (cmd.startsWith("SET_A:")) valA = cmd.substring(6);
    else if (cmd.startsWith("SET_B:")) valB = cmd.substring(6);
    else if (cmd.startsWith("SET_C:")) valC = cmd.substring(6);
    else if (cmd.startsWith("SET_D:")) valD = cmd.substring(6);

    // Value GET
    else if (cmd == "GET_A") Serial.println(valA);
    else if (cmd == "GET_B") Serial.println(valB);
    else if (cmd == "GET_C") Serial.println(valC);
    else if (cmd == "GET_D") Serial.println(valD);

    // Classic GET/SET for testing
    else if (cmd.startsWith("SET:")) {
      current_value = cmd.substring(4);
      Serial.println("Value updated");
    }
    else if (cmd == "GET_VALUE") {
      Serial.println(current_value);
    }

    // Get entire log
    else if (cmd == "GET_LOG") {
      File file = FILESYSTEM.open("/log.txt");
      if (file) {
        while (file.available()) {
          Serial.write(file.read());
        }
        file.close();
      } else {
        Serial.println(F("Can't open log.txt"));
      }
    }

    // Clear log
    else if (cmd == "CLEAR_LOG") {
      logging_enabled = false;
      FILESYSTEM.remove("/log.txt");
      delay(100);
      File check = FILESYSTEM.open("/log.txt");
      if (!check) Serial.println(F("Log cleared."));
      else {
        Serial.println(F("Log still exists!"));
        check.close();
      }
      logging_enabled = true;
    }
  }
}
