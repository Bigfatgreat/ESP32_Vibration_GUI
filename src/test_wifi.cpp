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

// Default MQTT credentials (used if nothing is stored)
const char* defaultMQTTServer = "10.4.32.78";

// Variables loaded from preferences
String storedSSID;
String storedPassword;
String storedMQTTServer;
String storedMQTTTopic;

// WiFi and MQTT objects
WiFiClient espClient;
PubSubClient mqttClient(espClient);
WebServer server(80); // for future HTTP serving

// Sensor simulation
struct SensorData {
  float AX, AY, AZ;  // Acceleration
  float VX, VY, VZ;  // Velocity
  float DX, DY, DZ;  // Distance
  float HX, HY, HZ;  // Height
  float TEMP;        // Temperature
};

bool readingActive = false;
unsigned long lastSensorUpdate = 0;
const unsigned long sensorInterval = 1000; // 1 second

// ----- Function Prototypes -----
void setupWiFi();
void connectToWiFi(const char* ssid, const char* password);
void sendSensorData();
void generateRandomData(SensorData &data);
void handleSerialCommands();
void mqttCallback(char* topic, byte* payload, unsigned int length);
void setupMQTT();
void reconnectMQTT();

// ----- Setup -----
void setup() {
  Serial.begin(115200);
  randomSeed(analogRead(0));
  
  // Initialize Preferences in RW mode
  preferences.begin("wifi-config", false);
  
  // Load stored WiFi credentials (if any)
  storedSSID = preferences.getString("ssid", "");
  storedPassword = preferences.getString("password", "");
  
  // Load stored MQTT credentials
  storedMQTTServer = preferences.getString("mqtt_server", defaultMQTTServer);
  storedMQTTTopic = preferences.getString("mqtt_topic", "");
  
  // Configure WiFi in AP+STA mode
  WiFi.mode(WIFI_AP_STA);
  WiFi.softAP(apSSID, apPassword);  // start AP mode for configuration
  
  // If WiFi credentials exist, try to connect
  if (storedSSID.length() > 0) {
    connectToWiFi(storedSSID.c_str(), storedPassword.c_str());
  } else {
    Serial.println("No WiFi credentials stored, running in AP mode.");
  }

  // Setup MQTT client
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
}

void loop() {
  handleSerialCommands();
  
  // Generate and send sensor data if reading is active
  if (readingActive && (millis() - lastSensorUpdate >= sensorInterval)) {
    sendSensorData();
    lastSensorUpdate = millis();
  }
  
  // Ensure MQTT stays connected
  if (!mqttClient.connected()) {
    reconnectMQTT();
  }
  mqttClient.loop();
}

// ----- WiFi Functions -----
void setupWiFi() {
  // Already configured in setup() with softAP mode
  Serial.println("WiFi setup complete (AP+STA mode).");
}

void connectToWiFi(const char* ssid, const char* password) {
  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nFailed to connect to WiFi");
  }
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
  while (!mqttClient.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (mqttClient.connect("ESP32Client")) {
      Serial.println("MQTT connected");
      mqttClient.publish("status", "ESP32 connected");
    } else {
      Serial.print("MQTT connect failed, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" - retrying in 2 seconds");
      delay(2000);
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

// ----- Command Handling -----
void handleSerialCommands() {
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
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
