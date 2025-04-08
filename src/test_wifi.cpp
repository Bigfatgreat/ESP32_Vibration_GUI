#include <Arduino.h>
#include <WiFi.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <PubSubClient.h>
#include <WebServer.h>

// ----- Global Variables & Definitions -----
Preferences preferences;
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
WebServer server(80); // For future HTTP serving

// Sensor simulation structure
struct SensorData {
  float AX, AY, AZ;   // Acceleration
  float VX, VY, VZ;   // Velocity
  float DX, DY, DZ;   // Distance
  float HX, HY, HZ;   // Height
  float TEMP;         // Temperature
};

bool readingActive = false;
unsigned long lastSensorUpdate = 0;
const unsigned long sensorInterval = 1000;  // 1 second

// ----- Task function prototypes -----
void sensorTask(void *pvParameters);
void serialTask(void *pvParameters);
void mqttTask(void *pvParameters);

// ----- Function Prototypes -----
void connectToWiFi(const char* ssid, const char* password);
void sendSensorData();
void generateRandomData(SensorData &data);
void handleSerialCommands();
void mqttCallback(char* topic, byte* payload, unsigned int length);
void reconnectMQTT();

//
// Setup
//
void setup() {
  Serial.begin(115200);
  randomSeed(analogRead(0));

  // Initialize Preferences (for WiFi/MQTT credentials)
  preferences.begin("wifi-config", false);
  storedSSID = preferences.getString("ssid", "");
  storedPassword = preferences.getString("password", "");
  storedMQTTServer = preferences.getString("mqtt_server", defaultMQTTServer);
  storedMQTTTopic = preferences.getString("mqtt_topic", "");

  // Setup WiFi in AP+STA mode for configuration
  WiFi.mode(WIFI_AP_STA);
  WiFi.softAP(apSSID, apPassword);

  // If WiFi credentials exist, try to connect (non-blocking)
  if (storedSSID.length() > 0) {
    Serial.print("Attempting to connect to saved WiFi: ");
    Serial.println(storedSSID);
    WiFi.begin(storedSSID.c_str(), storedPassword.c_str());
  } else {
    Serial.println("No WiFi credentials stored, running in AP mode.");
  }

  mqttClient.setServer(storedMQTTServer.c_str(), 1883);
  mqttClient.setCallback(mqttCallback);

  Serial.println("System ready");
  Serial.println("Available Commands:");
  Serial.println("  START_READING - Begin sensor data transmission");
  Serial.println("  STOP_READING  - Stop sensor data transmission");
  Serial.println("  SET_WIFI:ssid,password   - Save WiFi credentials");
  Serial.println("  CONNECT_WIFI  - Connect to saved WiFi");
  Serial.println("  DISCONNECT_WIFI - Disconnect WiFi");
  Serial.println("  SET_MQTT:server,topic    - Save MQTT credentials");
  Serial.println("  CONNECT_MQTT - Connect to MQTT broker");
  Serial.println("  DISCONNECT_MQTT - Disconnect from MQTT broker");
  Serial.println("  GET_STATUS - Get current system status");

  // Initialize the last sensor update time
  lastSensorUpdate = millis();

  // Create FreeRTOS tasks:
  // SensorTask: runs on core 1
  xTaskCreatePinnedToCore(sensorTask, "SensorTask", 4096, NULL, 1, NULL, 1);
  // SerialTask: runs on core 0 (or default)
  xTaskCreatePinnedToCore(serialTask, "SerialTask", 4096, NULL, 1, NULL, 0);
  // MQTTTask: runs on core 0 (or default)
  xTaskCreatePinnedToCore(mqttTask, "MQTTTask", 4096, NULL, 1, NULL, 0);
}

void loop() {
  // Leave loop empty – tasks handle everything.
}

//
// Task: SensorTask – Sends sensor data every sensorInterval if reading is active.
//
void sensorTask(void *pvParameters) {
  for (;;) {
    if (readingActive && (millis() - lastSensorUpdate >= sensorInterval)) {
      sendSensorData();
      lastSensorUpdate = millis();
    }
    // Give other tasks a chance to run
    vTaskDelay(10 / portTICK_PERIOD_MS);
  }
}

//
// Task: SerialTask – Reads incoming serial commands and processes them.
//
void serialTask(void *pvParameters) {
  for (;;) {
    handleSerialCommands();
    vTaskDelay(10 / portTICK_PERIOD_MS);
  }
}

//
// Task: MQTTTask – Ensures MQTT connectivity and processes the MQTT loop.
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
// Non-blocking Serial Command Handler
//
void handleSerialCommands() {
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    if (command.length() == 0) return;

    if (command == "START_READING") {
      readingActive = true;
      Serial.println("Starting sensor readings");
    } 
    else if (command == "STOP_READING") {
      readingActive = false;
      Serial.println("Stopping sensor readings");
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
        Serial.println("WiFi credentials saved");
      } else {
        Serial.println("Invalid SET_WIFI format. Use: SET_WIFI:ssid,password");
      }
    }
    else if (command == "CONNECT_WIFI") {
      if (storedSSID.length() > 0) {
        connectToWiFi(storedSSID.c_str(), storedPassword.c_str());
      } else {
        Serial.println("No WiFi credentials saved");
      }
    }
    else if (command == "DISCONNECT_WIFI") {
      WiFi.disconnect();
      Serial.println("WiFi disconnected");
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
        Serial.println("MQTT credentials saved");
      } else {
        Serial.println("Invalid SET_MQTT format. Use: SET_MQTT:server,topic");
      }
    }
    else if (command == "CONNECT_MQTT") {
      if (!mqttClient.connected()) {
        reconnectMQTT();
      } else {
        Serial.println("MQTT already connected");
      }
    }
    else if (command == "DISCONNECT_MQTT") {
      mqttClient.disconnect();
      Serial.println("MQTT disconnected");
    }
    else if (command == "GET_STATUS") {
      Serial.print("WiFi Status: ");
      if (WiFi.status() == WL_CONNECTED) {
        Serial.print("Connected to ");
        Serial.print(WiFi.SSID());
        Serial.print(", IP: ");
        Serial.println(WiFi.localIP());
      } else {
        Serial.println("Disconnected");
      }
      Serial.print("Sensor Reading: ");
      Serial.println(readingActive ? "Active" : "Inactive");
      Serial.print("MQTT: ");
      Serial.println(mqttClient.connected() ? "Connected" : "Disconnected");
    }
    else {
      Serial.println("Unknown command");
    }
  }
}

// ----- WiFi Functions -----
void connectToWiFi(const char* ssid, const char* password) {
  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  // Do not block here; let the main tasks and status checks handle connection
}

// ----- MQTT Functions -----
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
    Serial.print("Attempting MQTT connection...");
    if (mqttClient.connect("ESP32Client")) {
      Serial.println(" MQTT connected");
      mqttClient.publish("status", "ESP32 connected");
    } else {
      Serial.print(" MQTT connect failed, rc=");
      Serial.println(mqttClient.state());
      delay(500); // Short delay before next attempt
    }
  }
}

// ----- Sensor Data Functions -----
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

  // Publish sensor data via MQTT if connected and topic is set
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
