#include <Arduino.h>
#include "LittleFS.h"
#define FILESYSTEM LittleFS

bool logging_enabled = true;
unsigned long lastLogTime = 0;
const unsigned long logInterval = 10000;
String current_value = "N/A";

void setup() {
  Serial.begin(115200);
  if (!FILESYSTEM.begin(true)) {
    Serial.println(F("LittleFS Mount Failed"));
    return;
  }
  Serial.println(F("ESP32 Logger Ready"));
}

void loop() {
  if (logging_enabled && millis() - lastLogTime > logInterval) {
    lastLogTime = millis();
    float temp = random(200, 300) / 10.0;
    float hum = random(400, 600) / 10.0;

    File file = FILESYSTEM.open("/log.txt", FILE_APPEND);
    if (file) {
      file.printf("T:%.1f,H:%.1f,Time:%lu\n", temp, hum, millis() / 1000);
      file.close();
    }
  }

    if (Serial.available()) {
      String cmd = Serial.readStringUntil('\n');
      cmd.trim();
      if (cmd.startsWith("SET:")) {
    current_value = cmd.substring(4);
    Serial.println("Value updated");

  } else if (cmd == "GET_VALUE") {
    Serial.println(current_value);
  }

    if (cmd == "GET_LOG") {
      File file = FILESYSTEM.open("/log.txt");
      if (file) {
        while (file.available()) Serial.write(file.read());
        file.close();
      } else {
        Serial.println(F("Can't open log.txt"));
      }

    } else if (cmd == "CLEAR_LOG") {
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
