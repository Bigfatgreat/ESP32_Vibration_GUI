#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

WiFiClient espClient;
PubSubClient mqttClient(espClient);

const char* ssid = "SAAA-KKN";  
const char* password = "Ace@6489"; 
const char* mqtt_server = "10.4.32.78";  // Default MQTT server
const char* mqtt_server_spare_1 = "10.4.88.69";  // Spare server 1
const char* mqtt_server_spare_2 = "10.4.88.69";  // Spare server 2   
const char* mqtt_topic = "vibration/data";  
const char* mqtt_name = "master";
const char* host = "ACE";

unsigned long lastSend = 0;
const unsigned long sendInterval = 10000;  // Send every 10 seconds

void setup() {
  Serial.begin(115200);

  // Connecting to WiFi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected!");

  // Set MQTT server
  mqttClient.setServer(mqtt_server, 1883);
  
  // Connecting to MQTT server
  while (!mqttClient.connected()) {
    Serial.print("Connecting to MQTT...");
    if (mqttClient.connect("ESP32Client")) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.println(mqttClient.state());
      delay(2000);
    }
  }
}

// Function to send mock vibration data
void sendMockVibration() {
  StaticJsonDocument<256> doc;
  doc["AX"] = random(0, 1000) / 100.0;  // Random X-axis vibration data
  doc["AY"] = random(0, 1000) / 100.0;  // Random Y-axis vibration data
  doc["AZ"] = random(0, 1000) / 100.0;  // Random Z-axis vibration data
  doc["TEMP"] = 25.0 + random(-500, 500) / 100.0;  // Random temperature around 25°C

  String jsonStr;
  serializeJson(doc, jsonStr);

  // Publish to MQTT topic
  mqttClient.publish(mqtt_topic, jsonStr.c_str());

  // Print to Serial Monitor for debugging
  Serial.println("Published mock data: " + jsonStr);
}

void loop() {
  mqttClient.loop();  // Handle MQTT communication

  // Send mock vibration data every 'sendInterval' milliseconds
  if (millis() - lastSend > sendInterval) {
    lastSend = millis();
    sendMockVibration();
  }

  // Check for serial command to get WiFi status
  String cmd = Serial.readStringUntil('\n');
  cmd.trim();
  if (cmd == "GET_WIFI_STATUS") {
    if (WiFi.status() == WL_CONNECTED) {
      Serial.println("WiFi Connected: " + WiFi.localIP().toString());
    } else {
      Serial.println("WiFi Not Connected");
    }
  }
}
