#include <Arduino.h>
#include <WiFi.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <PubSubClient.h>
#include <WebServer.h>

// ----- Global Variables & Definitions -----
Preferences preferences;  // For permanent storage of credentials (instead of EEPROM)
const char* apSSID = "SAAA-KKN";
const char* apPassword = "Ace@6489";

// Default MQTT settings
const char* defaultMQTTServer = "10.4.32.78";

String storedSSID;
String storedPassword;
String storedMQTTServer;
String storedMQTTTopic;

WiFiClient espClient;
PubSubClient mqttClient(espClient);
WebServer server(80);  // For potential future HTTP requests

// Sensor simulation structure
struct SensorData {
  float AX, AY, AZ;
  float VX, VY, VZ;
  float DX, DY, DZ;
  float HX, HY, HZ;
  float TEMP;
};

volatile bool readingActive = false;
unsigned long lastSensorUpdate = 0;
const unsigned long sensorInterval = 1000;  // 1 second sensor data interval

// ----- Task Prototypes -----
// Runs on core 1: Send sensor data periodically if enabled.
void sensorTask(void *pvParameters);
// Runs on core 0: Read serial commands.
void serialTask(void *pvParameters);
// Runs on core 0: Maintain MQTT connection.
void mqttTask(void *pvParameters);

// ----- Function Prototypes -----
void handleSerialCommand(String command);
void sendSensorData();
void generateRandomData(SensorData &data);
void connectToWiFi(const char* ssid, const char* password);
void mqttCallback(char* topic, byte* payload, unsigned int length);
void reconnectMQTT();

//
// Setup
//
void setup() {
  Serial.begin(115200);
  randomSeed(analogRead(0));

  // Initialize Preferences in RW mode
  preferences.begin("wifi-config", false);
  storedSSID = preferences.getString("ssid", "");
  storedPassword = preferences.getString("password", "");
  storedMQTTServer = preferences.getString("mqtt_server", defaultMQTTServer);
  storedMQTTTopic = preferences.getString("mqtt_topic", "");

  // Setup WiFi in AP+STA mode for configuration
  WiFi.mode(WIFI_AP_STA);
  WiFi.softAP(apSSID, apPassword);

  // If there are stored credentials, try connecting (non-blocking)
  if (storedSSID.length() > 0) {
    Serial.print("Connecting to saved WiFi: ");
    Serial.println(storedSSID);
    WiFi.begin(storedSSID.c_str(), storedPassword.c_str());
  } else {
    Serial.println("No WiFi credentials stored; running in AP mode.");
  }

  // Setup MQTT client
  mqttClient.setServer(storedMQTTServer.c_str(), 1883);
  mqttClient.setCallback(mqttCallback);

  Serial.println("System ready. Listening for commands...");
  Serial.println("Commands:");
  Serial.println("  START_READING");
  Serial.println("  STOP_READING");
  Serial.println("  SET_WIFI:ssid,password");
  Serial.println("  CONNECT_WIFI");
  Serial.println("  DISCONNECT_WIFI");
  Serial.println("  SET_MQTT:server,topic");
  Serial.println("  CONNECT_MQTT");
  Serial.println("  DISCONNECT_MQTT");
  Serial.println("  GET_STATUS");

  lastSensorUpdate = millis();

  // Create FreeRTOS tasks:
  xTaskCreatePinnedToCore(sensorTask, "SensorTask", 4096, NULL, 1, NULL, 1);
  xTaskCreatePinnedToCore(serialTask, "SerialTask", 4096, NULL, 1, NULL, 0);
  xTaskCreatePinnedToCore(mqttTask, "MQTTTask", 4096, NULL, 1, NULL, 0);
}

void loop() {
  // Main loop empty: tasks handle processing
}

//
// sensorTask: Sends sensor data every sensorInterval when readingActive
//
void sensorTask(void *pvParameters) {
  for (;;) {
    if (readingActive && (millis() - lastSensorUpdate >= sensorInterval)) {
      sendSensorData();
      lastSensorUpdate = millis();
    }
    vTaskDelay(10 / portTICK_PERIOD_MS);
  }
}

//
// serialTask: Continuously checks for serial commands (non-blocking)
//
void serialTask(void *pvParameters) {
  for (;;) {
    if (Serial.available()) {
      String command = Serial.readStringUntil('\n');
      command.trim();
      if (command.length() > 0) {
        handleSerialCommand(command);
      }
    }
    vTaskDelay(10 / portTICK_PERIOD_MS);
  }
}

//
// mqttTask: Ensures MQTT connectivity and runs the MQTT loop.
//
void mqttTask(void *pvParameters) {
  for (;;) {
    if (!mqttClient.connected()) {
      reconnectMQTT();
    }
    mqttClient.loop();
    vTaskDelay(100 / portTICK_PERIOD_MS);
  }
}

//
// Handle serial commands – only accept complete commands.
// The ESP32 is expected to output sensor data as one complete JSON line.
// Commands for WiFi or MQTT should follow a clear format.
//
void handleSerialCommand(String command) {
  if (command == "START_READING") {
    readingActive = true;
    Serial.println("ACK:START_READING");
  }
  else if (command == "STOP_READING") {
    readingActive = false;
    Serial.println("ACK:STOP_READING");
  }
  else if (command.startsWith("SET_WIFI:")) {
    int colonPos = command.indexOf(':');
    int commaPos = command.indexOf(',');
    if (colonPos != -1 && commaPos != -1) {
      String ssid = command.substring(colonPos + 1, commaPos);
      String password = command.substring(commaPos + 1);
      preferences.putString("ssid", ssid);
      preferences.putString("password", password);
      storedSSID = ssid;
      storedPassword = password;
      Serial.println("ACK:SET_WIFI");
    } else {
      Serial.println("ERR:SET_WIFI format invalid");
    }
  }
  else if (command == "CONNECT_WIFI") {
    if (storedSSID.length() > 0) {
      connectToWiFi(storedSSID.c_str(), storedPassword.c_str());
    } else {
      Serial.println("ERR:No WiFi credentials");
    }
  }
  else if (command == "DISCONNECT_WIFI") {
    WiFi.disconnect();
    Serial.println("ACK:DISCONNECT_WIFI");
  }
  else if (command.startsWith("SET_MQTT:")) {
    int colonPos = command.indexOf(':');
    int commaPos = command.indexOf(',');
    if (colonPos != -1 && commaPos != -1) {
      String mqttServer = command.substring(colonPos + 1, commaPos);
      String mqttTopic = command.substring(commaPos + 1);
      preferences.putString("mqtt_server", mqttServer);
      preferences.putString("mqtt_topic", mqttTopic);
      storedMQTTServer = mqttServer;
      storedMQTTTopic = mqttTopic;
      mqttClient.setServer(storedMQTTServer.c_str(), 1883);
      Serial.println("ACK:SET_MQTT");
    } else {
      Serial.println("ERR:SET_MQTT format invalid");
    }
  }
  else if (command == "CONNECT_MQTT") {
    if (!mqttClient.connected()) {
      reconnectMQTT();
    } else {
      Serial.println("ACK:MQTT already connected");
    }
  }
  else if (command == "DISCONNECT_MQTT") {
    mqttClient.disconnect();
    Serial.println("ACK:DISCONNECT_MQTT");
  }
  else if (command == "GET_STATUS") {
    Serial.print("STATUS:WiFi:");
    if (WiFi.status() == WL_CONNECTED) {
      Serial.print("CONNECTED:");
      Serial.print(WiFi.SSID());
      Serial.print(":");
      Serial.println(WiFi.localIP());
    } else {
      Serial.println("DISCONNECTED");
    }
    Serial.print("STATUS:Sensor:");
    Serial.println(readingActive ? "Active" : "Inactive");
    Serial.print("STATUS:MQTT:");
    Serial.println(mqttClient.connected() ? "Connected" : "Disconnected");
  }
  else {
    Serial.println("ERR:Unknown command");
  }
}

//
// WiFi Functions
//
void connectToWiFi(const char* ssid, const char* password) {
  Serial.print("CONNECTING_WIFI:");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    attempts++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("WIFI_STATUS:CONNECTED:");
    Serial.print(ssid);
    Serial.print(":");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("WIFI_STATUS:DISCONNECTED");
  }
}

//
// MQTT Functions
//
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  Serial.print("MQTT Message on [");
  Serial.print(topic);
  Serial.print("]: ");
  for (unsigned int i = 0; i < length; i++) {
    Serial.print((char)payload[i]);
  }
  Serial.println();
}

void reconnectMQTT() {
  if (!mqttClient.connected()) {
    Serial.print("MQTT Connecting...");
    if (mqttClient.connect("ESP32Client")) {
      Serial.println(" Connected");
      mqttClient.publish("status", "ESP32 connected");
    } else {
      Serial.print(" MQTT connect failed, rc=");
      Serial.println(mqttClient.state());
      delay(500);
    }
  }
}

//
// Sensor Data Functions
//
void sendSensorData() {
  SensorData data;
  generateRandomData(data);

  StaticJsonDocument<256> doc;
  doc["AX_1"] = data.AX;
  doc["AY_1"] = data.AY;
  doc["AZ_1"] = data.AZ;
  doc["VX_1"] = data.VX;
  doc["VY_1"] = data.VY;
  doc["VZ_1"] = data.VZ;
  doc["DX_1"] = data.DX;
  doc["DY_1"] = data.DY;
  doc["DZ_1"] = data.DZ;
  doc["HX_1"] = data.HX;
  doc["HY_1"] = data.HY;
  doc["HZ_1"] = data.HZ;
  doc["TEMP_1"] = data.TEMP;

  String output;
  serializeJson(doc, output);
  Serial.println(output);
  Serial.flush();

  if (mqttClient.connected() && storedMQTTTopic.length() > 0) {
    mqttClient.publish(storedMQTTTopic.c_str(), output.c_str());
  }
}

void generateRandomData(SensorData &data) {
  data.AX = random(90, 110) / 10.0;
  data.AY = random(90, 110) / 10.0;
  data.AZ = random(90, 110) / 10.0;
  data.VX = random(1, 50) / 10.0;
  data.VY = random(1, 50) / 10.0;
  data.VZ = random(1, 50) / 10.0;
  data.DX = random(100, 1000) / 10.0;
  data.DY = random(100, 1000) / 10.0;
  data.DZ = random(100, 1000) / 10.0;
  data.HX = random(500, 1500) / 10.0;
  data.HY = random(500, 1500) / 10.0;
  data.HZ = random(500, 1500) / 10.0;
  data.TEMP = random(200, 350) / 10.0;
}
