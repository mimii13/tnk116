/*
 * TNK116 - Internet of Things
 * Sketch for blink
 * Board Arduino UNO
 * 1 x green LED
 * 1 x red LED
 * 1 x DHT22 (Temperature/Humidity sensor)
 */

// Including 3rd party software for reading DHT22.
#include "DHT.h"
#include "Adafruit_Sensor.h"

// Declaring pin and sensor type.
// Todo:Define the DHT pin, type and declare a DHT object
#define  DHTPIN 11
#define DHTTYPE DHT22

DHT dht(DHTPIN, DHTTYPE);

// Declaring variable to store LED instructions.
int type = -1;
int length = -1;

// Selecting the pins for different purpose.
const int INTERNAL_LED = 13;

int internalLedFrequency = 0;
int internalLedCounter = 0;
int internalLedStatus = 0;
int measuringInterval = 0;
int measuringCounter = 0;

// This method sends measurements to the Raspberry pi over the serial
// connection. The data is sent in a TLV structure. [Type][Length][Value].
// The size of the type field is 1 byte.
// The size of the length field is 2 bytes.
// The size of the value field varies.
void sendData(int type, String value) {
	// Printing the type.
	Serial.print(type);

	// Printing the length.
	int length = value.length();
	if (length < 10) {
		Serial.print("0");
	}

	Serial.print(value.length());

	// Printing the value.
	Serial.print(value);
}

// This method handles messages received from the Raspberry Pi.
// The type is used for identifying the type of message.
void handleMessage(int type, char value[]) {
	// Setting the interval of measurement readings.
	if (type == 1) {
		// Reads the values of the message.
		char parsedValue[length + 1];
		for (int i = 0; i < length; i++) {
			parsedValue[i] = value[i];
		}

		// Adds a \0 to make the ascii-to-integer code to work.
		parsedValue[length] = '\0';

		// Saving the measurement insterval by converting ascii text to integer.
		internalLedFrequency = atoi(parsedValue);

	} else if (type == 2) {
		// Reads the values of the message.
		char parsedValue[length + 1];
		for (int i = 0; i < length; i++) {
			parsedValue[i] = value[i];
		}

		// Adds a \0 to make the ascii-to-integer code to work.
		parsedValue[length] = '\0';

		// Saving the measurement insterval by converting ascii text to integer.
		measuringInterval = atoi(parsedValue);
	}
}

// This method reads data from the serial connection.
// The method extracts the type and length and sends the message to the handler
// when all bytes have arrived.
void receiveData() {
	// Checks if no message is in the pipe.
	if (type == -1) {
		// Checks if all bytes for the type and length has arrived.
		if (Serial.available() >= 3) {
			// Creates a byte array and reads the type.
			char typeBuffer[2];
			Serial.readBytes(typeBuffer, 1);

			// Adds a \0 to make the ascii-to-integer code to work.
			typeBuffer[1] = '\0';

			// Saves the type as a integer.
			type = atoi(typeBuffer);


			// Creates a byte array and reads the length.
			char lengthBuffer[3];
			Serial.readBytes(lengthBuffer, 2);

			// Adds a \0 to make the ascii-to-integer code to work.
			lengthBuffer[2] = '\0';

			// Saves the length as a integer.
			length = atoi(lengthBuffer);
		}
	}

	// Checks if a message is in the pipe.
	if (type != -1) {
		// Checks if all bytes for the message has arrived.
		if (Serial.available() >= length) {
			// Creates a byte array and reads the type.
			char valueBuffer[length];
			Serial.readBytes(valueBuffer, length);

			// Handles the message.
			handleMessage(type, valueBuffer);

			// Setting the message as handled by setting the type to NULL.
			type = -1;
		}
	}
}


void setup() {
	// Setup for that runs once in the beginning.
	// Defining the type of pins, in this case output.
	pinMode(INTERNAL_LED, OUTPUT);

	// Todo: Initializing the DHT sensor.
        dht.begin();

	// Starting a serial connection.
	Serial.begin(9600);
}

// This is the main loop of the Arduino code.
void loop() {
	receiveData();

	if (internalLedFrequency > 0) {
		// Checking if the measurement shall be collected.
		internalLedCounter = internalLedCounter % internalLedFrequency;
		if (internalLedCounter == 0) {
			if (internalLedStatus == 0) {
				digitalWrite(INTERNAL_LED, HIGH);
				internalLedStatus = 1;
			} else {
				digitalWrite(INTERNAL_LED, LOW);
				internalLedStatus = 0;
			}

			// Creating a string representation of the temperature.
			String iledOutput = "";
			char statusChar[2];
			dtostrf(internalLedStatus, 1, 0, statusChar);
			for (int i = 0; i < 2; i++) {
				iledOutput += statusChar[i];
			}

			// Sending the data to the Raspberry Pi.
			// Todo: Set this type number to match the gateway code.
			sendData(1, iledOutput);
			internalLedCounter = internalLedCounter + 1;
		} else {
			internalLedCounter = internalLedCounter + 1;
		}
	} else {
		if (internalLedStatus == 1) {
			digitalWrite(INTERNAL_LED, LOW);
			internalLedStatus = 0;
		}
	}
	// Collecting mesurements.
	if (measuringInterval > 0) {
		// Checking if the measurement shall be collected.
		measuringCounter = measuringCounter % measuringInterval;
		if (measuringCounter == 0) {

			// Todo Reading the temperature from the sensor.
			float temperature = dht.readTemperature();
			if (!isnan(temperature)) {
				// Creating a string representation of the temperature.
				String temperatureOutput = "";
				char temperatureChar[6];
				
				// Todo: convert the temperature to string using dtostrf
                                dtostrf(temperature, 4, 1, temperatureChar);
                                
                                
                                for (int i = 0; i < 6; i++){
                                  temperatureOutput += temperatureChar[i];
                                }
                                
				// Sending the data to the Raspberry Pi.
				// Todo: Set this type number to match the gateway code.
				sendData(2, temperatureOutput);

				measuringCounter = measuringCounter + 1;
			}
		} else {
			measuringCounter = measuringCounter + 1;
		}
	}
	// Waiting 1 second.
	delay(1000);
}
