#include <Arduino.h>

#include "FS.h"
#include "SPIFFS.h"

void setup() {
  Serial.begin(9600);
  if (!SPIFFS.begin(true)) {
    Serial.println("SPIFFS failed");
    return;
  }
}

  void loop() {
    
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    if (cmd == "GET_LOG") {
      File file = SPIFFS.open("/log.txt");
      while (file.available()) {
        Serial.write(file.read()); // or Serial.println(file.readStringUntil('\n'));
      }
      file.close();
    } else if (cmd == "LED_ON") {
      digitalWrite(2, HIGH);
    }
  }
  }

