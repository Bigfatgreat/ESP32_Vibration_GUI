#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

WiFiClient espClient;
PubSubClient mqttClient(espClient);

const char* ssid = "SAAA-KKN";  
const char* password = "Ace@6489"; 
const char* mqtt_server = "10.4.32.78";
const char* mqtt_server_spare_1 = "10.4.88.69";
const char* mqtt_server_spare_2 = "10.4.88.69";   
const char* mqtt_topic = "";  
const char* mqtt_name = "master";
const char* host = "ACE";

unsigned long lastSend = 0;
const unsigned long sendInterval = 10000;

void setup() {
  Serial.begin(115200);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("WiFi connected");

  mqttClient.setServer(mqtt_server, 1883);
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

void sendMockVibration() {
  StaticJsonDocument<256> doc;
  doc["AX"] = random(0, 1000) / 100.0;
  doc["AY"] = random(0, 1000) / 100.0;
  doc["AZ"] = random(0, 1000) / 100.0;
  doc["TEMP"] = 25.0 + random(-500, 500) / 100.0;

  String jsonStr;
  serializeJson(doc, jsonStr);
  mqttClient.publish(mqtt_topic, jsonStr.c_str());

  Serial.println("Published mock data: " + jsonStr);
}

void loop() {
  mqttClient.loop();

  if (millis() - lastSend > sendInterval) {
    lastSend = millis();
    sendMockVibration();
  }
  
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
