#include <ArduinoJson.h>

bool stopReading = false;  // Flag to control sensor reading

void setup() {
  Serial.begin(115200);  // Start the serial communication
  randomSeed(analogRead(0));  // Seed for random number generator
}

void loop() {
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');  // Read the command from serial
    command.trim();

    if (command == "STOP_READING") {
      stopReading = true;  // Stop reading sensor data
      Serial.println("Sensor reading stopped.");
    } else if (command == "START_READING") {
      stopReading = false;  // Start reading sensor data
      Serial.println("Sensor reading started.");
    }
  }

  if (!stopReading) {
    // Generate random values for the sensor data
    float AX_C = random(100, 500) / 100.0;  // Simulating AX_C
    float AY_C = random(100, 500) / 100.0;  // Simulating AY_C
    float AZ_C = random(100, 500) / 100.0;  // Simulating AZ_C
    int VX = random(0, 100);                // Simulating VX
    int VY = random(0, 100);                // Simulating VY
    int VZ = random(0, 100);                // Simulating VZ
    int TEMP = random(10, 30);              // Simulating Temperature

    // Simulate more data
    int DX = random(0, 50);  // Simulating DX (Distance)
    int DY = random(0, 50);  // Simulating DY
    int DZ = random(0, 50);  // Simulating DZ
    int HX = random(0, 100); // Simulating HX (Height)
    int HkDJ = random(0, 100); // Simulating HkDJ
    int HZZ = random(0, 100);  // Simulating HZZ

    // Create a JSON object to store the data
    StaticJsonDocument<512> doc;

    // Adding random values to the JSON document
    String AX_T = "AX_1";
    String AY_T = "AY_1";
    String AZ_T = "AZ_1";
    String VX_T = "VX_1";
    String VY_T = "VY_1";
    String VZ_T = "VZ_1";
    String TEMP_T = "TEMP_1";
    String DX_T = "DX_1";
    String DY_T = "DY_1";
    String DZ_T = "DZ_1";
    String HX_T = "HX_1";
    String HkDJ_T = "HkDJ_1";
    String HZZ_T = "HZZ_1";

    // Fill the JSON document with simulated data
    doc[AX_T] = AX_C;
    doc[AY_T] = AY_C;
    doc[AZ_T] = AZ_C;
    doc[VX_T] = VX;
    doc[VY_T] = VY;
    doc[VZ_T] = VZ;
    doc[TEMP_T] = TEMP;
    doc[DX_T] = DX;
    doc[DY_T] = DY;
    doc[DZ_T] = DZ;
    doc[HX_T] = HX;
    doc[HkDJ_T] = HkDJ;
    doc[HZZ_T] = HZZ;

    // Serialize the JSON object into a string
    String jsonString;
    serializeJson(doc, jsonString);

    // Send the JSON data over Serial to the GUI (or MQTT if used)
    Serial.println(jsonString);

    // Wait for 1 second before the next iteration
    delay(1000);  // Adjust this delay as needed
  }
}
