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

// Mode flags
enum Mode {SEND_DATA_MODE, RECEIVE_DATA_MODE};
Mode currentMode = SEND_DATA_MODE;

// Wi-Fi connection flag
volatile bool isWiFiConnecting = false;

// Function Prototypes
void handleSerialCommand(String command);
void sendSensorData();
void generateRandomData(SensorData &data);
void connectToWiFi(const char* ssid, const char* password);
void mqttCallback(char* topic, byte* payload, unsigned int length);
void reconnectMQTT();

// Wi-Fi Event Handlers
void connected_to_ap(WiFiEvent_t wifi_event, WiFiEventInfo_t wifi_info) {
  Serial.println("[+] Connected to the WiFi network");
}

void disconnected_from_ap(WiFiEvent_t wifi_event, WiFiEventInfo_t wifi_info) {
  Serial.println("[-] Disconnected from the WiFi AP");
  WiFi.begin(storedSSID.c_str(), storedPassword.c_str());  // Attempt reconnect if Wi-Fi credentials exist
}

void got_ip_from_ap(WiFiEvent_t wifi_event, WiFiEventInfo_t wifi_info) {
  Serial.print("[+] Local ESP32 IP: ");
  Serial.println(WiFi.localIP());
}

// Setup
void setup() {
  Serial.begin(115200);
  delay(1000);

  // Initialize Preferences in RW mode
  preferences.begin("wifi-config", false);
  storedSSID = preferences.getString("ssid", "");
  storedPassword = preferences.getString("password", "");
  storedMQTTServer = preferences.getString("mqtt_server", defaultMQTTServer);
  storedMQTTTopic = preferences.getString("mqtt_topic", "");

  // Setup Wi-Fi event handlers
  WiFi.onEvent(connected_to_ap, ARDUINO_EVENT_WIFI_STA_CONNECTED);
  WiFi.onEvent(got_ip_from_ap, ARDUINO_EVENT_WIFI_STA_GOT_IP);
  WiFi.onEvent(disconnected_from_ap, ARDUINO_EVENT_WIFI_STA_DISCONNECTED);

  // Setup MQTT client
  mqttClient.setServer(storedMQTTServer.c_str(), 1883);
  mqttClient.setCallback(mqttCallback);

  Serial.println("System Ready. Waiting for commands...");
}

void loop() {
  // Check if a serial command is available
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    if (command.length() > 0) {
      handleSerialCommand(command);
    }
  }

  // Check if we need to reconnect MQTT (only when in MQTT mode)
  if (mqttClient.connected()) {
    mqttClient.loop();  // Continue processing MQTT loop
  }
  delay(100);  // Small delay to prevent overwhelming the loop
}

// Handle serial commands
void handleSerialCommand(String command) {
  if (command == "START_READING") {
    readingActive = true;
    Serial.println("ACK:START_READING");
  }
  else if (command == "STOP_READING") {
    readingActive = false;
    Serial.println("ACK:STOP_READING");
  }
  else if (command == "WIFI_CN") {  // Start Wi-Fi connection
    if (isWiFiConnecting) {
      Serial.println("Wi-Fi connection already in progress.");
    } else {
      isWiFiConnecting = true;
      Serial.println("Connecting to Wi-Fi...");
      connectToWiFi(storedSSID.c_str(), storedPassword.c_str());
    }
  }
  else if (command == "WIFI_DCN") {  // Disconnect Wi-Fi
    WiFi.disconnect();
    Serial.println("Wi-Fi Disconnected");
    // Ensure the ESP32 does not automatically reconnect
    WiFi.mode(WIFI_OFF);  // Disable Wi-Fi temporarily to prevent auto-reconnect
    delay(500);  // Wait for a short time before resetting Wi-Fi mode
    WiFi.mode(WIFI_STA);  // Set Wi-Fi mode back to STA (station mode) if needed later
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
  else if (command == "MQTT_CN") {  // Start MQTT connection
    if (!mqttClient.connected()) {
      Serial.println("Connecting to MQTT...");
      reconnectMQTT();
    } else {
      Serial.println("MQTT already connected");
    }
  }
  else if (command == "MQTT_DCN") {  // Disconnect MQTT
    mqttClient.disconnect();
    Serial.println("MQTT Disconnected");
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
  else if (command == "GET_STATUS") {
    // Get the status of Wi-Fi and MQTT
    Serial.print("STATUS:WiFi:");
    if (WiFi.status() == WL_CONNECTED) {
      Serial.print("CONNECTED:");
      Serial.print(WiFi.SSID());
      Serial.print(":");
      Serial.println(WiFi.localIP());
    } else {
      Serial.println("DISCONNECTED");
    }

    Serial.print("STATUS:MQTT:");
    if (mqttClient.connected()) {
      Serial.println("CONNECTED");
    } else {
      Serial.println("DISCONNECTED");
    }
  }
  else {
    Serial.println("ERR:Unknown command");
  }
}


// Wi-Fi Functions
void connectToWiFi(const char* ssid, const char* password) {
  WiFi.begin(ssid, password);
  unsigned long startMillis = millis();
  while (WiFi.status() != WL_CONNECTED && (millis() - startMillis) < 10000) {  // 10 seconds timeout
    delay(500);
    Serial.print(".");
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("Wi-Fi connected");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
    isWiFiConnecting = false;  // Reset flag after successful connection
  } else {
    Serial.println("Failed to connect to Wi-Fi");
    isWiFiConnecting = false;  // Reset flag on failure
  }
}

// MQTT Functions
void reconnectMQTT() {
  while (!mqttClient.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (mqttClient.connect("ESP32Client")) {
      Serial.println("connected");
      mqttClient.publish("status", "ESP32 connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(mqttClient.state());
      delay(5000);
    }
  }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  Serial.print("MQTT Message received on [");
  Serial.print(topic);
  Serial.print("]: ");
  for (unsigned int i = 0; i < length; i++) {
    Serial.print((char)payload[i]);
  }
  Serial.println();
}

// Sensor Data Functions
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
