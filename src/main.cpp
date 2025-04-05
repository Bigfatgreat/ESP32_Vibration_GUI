#include <WiFi.h>
#include <PubSubClient.h>
#include <EEPROM.h>
#include <ESPmDNS.h>
#include <WebServer.h>
#include <ArduinoJson.h>  // Add ArduinoJson library to handle JSON

// WiFi and MQTT Configuration
const char* ssid = "SAAA-KKN";  
const char* password = "Ace@6489"; 
String mqtt_server_number;
String mqtt_topics;
String device_name;
String mqtt_server_spare_1;
String mqtt_server_spare_2;
String mqtt_server;
String mqtt_topic;
const char* host = "ACE";

WiFiClient espClient;
PubSubClient mqttClient(espClient);
WebServer server(80);  // Initialize the WebServer on port 80

// EEPROM Addresses for storing configurations
#define EEPROM_ADDRESS_DEVICE_NAME 0
#define EEPROM_ADDRESS_MQTT_SERVER 32
#define EEPROM_ADDRESS_MQTT_TOPIC 64
#define EEPROM_ADDRESS_MQTT_SERVER_SPARE_1 96
#define EEPROM_ADDRESS_MQTT_SERVER_SPARE_2 128

// Modbus Sensor Readings (Example)
float AX_C = 0, AY_C = 0, AZ_C = 0;  // Accelerometer values
int VX = 0, VY = 0, VZ = 0;           // Velocity values
int TEMP = 0;                          // Temperature value

void setup() {
  Serial.begin(115200);
  EEPROM.begin(512);  // Initialize EEPROM with 512 bytes

  // Load settings from EEPROM
  device_name = readStringFromEEPROM(EEPROM_ADDRESS_DEVICE_NAME);
  mqtt_server_number = readStringFromEEPROM(EEPROM_ADDRESS_MQTT_SERVER);
  mqtt_topics = readStringFromEEPROM(EEPROM_ADDRESS_MQTT_TOPIC);
  mqtt_server_spare_1 = readStringFromEEPROM(EEPROM_ADDRESS_MQTT_SERVER_SPARE_1);
  mqtt_server_spare_2 = readStringFromEEPROM(EEPROM_ADDRESS_MQTT_SERVER_SPARE_2);
  
  // Set MQTT server and topic
  mqtt_server = mqtt_server_number.c_str();
  mqtt_topic = mqtt_topics.c_str();

  // Connect to WiFi
  setup_wifi();

  // Setup WebServer for device configuration
  setupWebServer();

  // Setup MQTT client
  mqttClient.setServer(mqtt_server.c_str(), 1883);
  mqttClient.setCallback(mqttCallback);
  
  // Start the WebServer
  server.begin();
}

void setup_wifi() {
  Serial.print("Connecting to WiFi...");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }
  Serial.println("Connected to WiFi");

  if (!MDNS.begin(host)) {
    Serial.println("Error setting up mDNS responder!");
    while (1) {
      delay(1000);
    }
  }
  Serial.println("mDNS responder started");
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Message arrived on topic: ");
  Serial.print(topic);
  Serial.print(" with message: ");
  for (unsigned int i = 0; i < length; i++) {
    Serial.print((char)payload[i]);
  }
  Serial.println();
}

void reconnect_mqtt() {
  int retryCount = 0;
  while (!mqttClient.connected()) {
    if (retryCount > 16) {
      Serial.println("Reached maximum retry attempts, restarting ESP.");
      ESP.restart();
      break;  // Skip reconnect attempts
    }
    Serial.print("Attempting MQTT connection...");
    if (mqttClient.connect("ESP32Client")) {
      Serial.println("connected");
      break;
    } else {
      Serial.print("failed, rc=");
      Serial.println(mqttClient.state());
      retryCount++;  // Increment retry count
      delay(2000);  // Wait 2 seconds before retrying
    }
  }
}

void mqttLoop() {
  if (!mqttClient.connected()) {
    reconnect_mqtt();
  }
  mqttClient.loop();  // Handle MQTT messages
}

void setupWebServer() {
  // Web server to update settings through HTTP requests
  server.on("/", HTTP_GET, []() {
    server.sendHeader("Connection", "close");
    server.send(200, "text/html", "<h1>Device Configuration</h1>");
  });

  // Save device settings (device name, MQTT server, topic)
  server.on("/saveSettings", HTTP_POST, []() {
    if (server.hasArg("device_name")) {
      device_name = server.arg("device_name");
      saveStringToEEPROM(EEPROM_ADDRESS_DEVICE_NAME, device_name);
      Serial.println("Device name updated");
    }

    if (server.hasArg("mqtt_server")) {
      mqtt_server_number = server.arg("mqtt_server");
      saveStringToEEPROM(EEPROM_ADDRESS_MQTT_SERVER, mqtt_server_number);
      mqtt_server = mqtt_server_number.c_str();
      Serial.println("MQTT Server updated");
    }

    if (server.hasArg("mqtt_topic")) {
      mqtt_topics = server.arg("mqtt_topic");
      saveStringToEEPROM(EEPROM_ADDRESS_MQTT_TOPIC, mqtt_topics);
      mqtt_topic = mqtt_topics.c_str();
      Serial.println("MQTT Topic updated");
    }

    server.send(200, "text/plain", "Settings updated");
  });

  // Start the server
  server.begin();
}

void saveStringToEEPROM(int address, String data) {
  int length = data.length();
  EEPROM.write(address, length & 0xFF);  // Lower byte
  EEPROM.write(address + 1, (length >> 8) & 0xFF);  // Higher byte
  for (int i = 0; i < length; i++) {
    EEPROM.write(address + 2 + i, data[i]);
  }
  EEPROM.commit();
  Serial.println("Saved to EEPROM: " + data);
}

String readStringFromEEPROM(int address) {
  int length = EEPROM.read(address) | (EEPROM.read(address + 1) << 8);
  char buffer[length + 1];
  for (int i = 0; i < length; i++) {
    buffer[i] = EEPROM.read(address + 2 + i);
  }
  buffer[length] = '\0';  // Null-terminate the string
  return String(buffer);
}

void loop() {
  server.handleClient();  // Handle HTTP requests
  mqttLoop();  // Keep MQTT connected and handle messages
  
  // Send sensor data to MQTT (this part is kept from your old code)
  StaticJsonDocument<512> doc;
  doc["AX_1"] = AX_C;
  doc["AY_1"] = AY_C;
  doc["AZ_1"] = AZ_C;
  doc["VX_1"] = VX;
  doc["VY_1"] = VY;
  doc["VZ_1"] = VZ;
  doc["TEMP_1"] = TEMP * 0.01;

  String jsonString;
  serializeJson(doc, jsonString);
  sendToMQTT(mqtt_topic, jsonString);

  delay(5000);  // Wait for 5 seconds before sending the next message
}

void sendToMQTT(String topic, String message) {
  if (mqttClient.connected()) {
    mqttClient.publish(topic.c_str(), message.c_str());
    Serial.print("Sent to MQTT: ");
    Serial.println(message);
  } else {
    Serial.println("MQTT not connected");
  }
}
