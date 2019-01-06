#include <Arduino_FreeRTOS.h>
#include <Adafruit_NeoPixel.h>

// PIN connected to the NeoPixel
#define PIN 6

// Size of the Neopixel Ring
#define STRIPSIZE 24

// Various vars
char s;
bool interrupt = false;
int brightness = 80;

Adafruit_NeoPixel strip = Adafruit_NeoPixel(STRIPSIZE, PIN, NEO_GRB + NEO_KHZ800);


// Reset the Neopixel to all black
void animReset() {
  for (uint16_t i = 0; i < strip.numPixels(); i++) {
    strip.setPixelColor(i, strip.Color(0, 0, 0));
    strip.show();
  }
}

// Green wheel
uint32_t GWheel(byte WheelPos) {
  if (WheelPos < 85) {
    return strip.Color(0,  255 - WheelPos * 3, 0);
  } else if (WheelPos < 300) {
    WheelPos -= 85;
    return strip.Color(0, 0, 0);
  } else {
    WheelPos -= 170;
    return strip.Color(0, WheelPos * 3, 0);
  }
}

// Blue wheel
uint32_t BWheel(byte WheelPos) {
  if (WheelPos < 85) {
    return strip.Color(0, 0, 255 - WheelPos * 3);
  } else if (WheelPos < 300) {
    WheelPos -= 85;
    return strip.Color(0, 0, 0);
  } else {
    WheelPos -= 170;
    return strip.Color(0, 0, WheelPos * 3);
  }
}

// Rainbow wheel
uint32_t RGBWheel(byte WheelPos) {
  WheelPos = 255 - WheelPos;
  if (WheelPos < 85) {
    return strip.Color(255 - WheelPos * 3, 0, WheelPos * 3);
  }
  if (WheelPos < 170) {
    WheelPos -= 85;
    return strip.Color(0, WheelPos * 3 , 255 - WheelPos * 3);
  }
  WheelPos -= 170;
  return strip.Color(WheelPos * 3 , 255 - WheelPos * 3 , 0);
}


// Tasks
void TaskRing( void *pvParameters );
void TaskSerial( void *pvParameters );

void setup() {

  // initialize serial communication with baudrate of 9600
  Serial.begin(9600);
  strip.begin();

  // set initial Neopixel brightness
  strip.setBrightness(brightness);
  strip.show();

  // Now set up two tasks to run independently.


  xTaskCreate(
    TaskSerial
    ,  (const portCHAR *) "serial"
    ,  128  // Stack size
    ,  NULL
    ,  2  // Priority
    ,  NULL );

  xTaskCreate(
    TaskRing
    ,  (const portCHAR *)"ring"   // A name just for humans
    ,  128  // This stack size can be checked & adjusted by reading the Stack Highwater
    ,  NULL
    ,  2  // Priority, with 3 (configMAX_PRIORITIES - 1) being the highest, and 0 being the lowest.
    ,  NULL );


  // Now the task scheduler, which takes over control of scheduling individual tasks, is automatically started.
}

void loop()
{
  // Empty. Things are done in Tasks.
}

/*--------------------------------------------------*/
/*---------------------- Tasks ---------------------*/
/*--------------------------------------------------*/

void TaskRing(void *pvParameters)  // This is a task.
{
  (void) pvParameters;

  for (;;) // A Task shall never return or exit.
  {

    if (s == '0') {
      animReset();
    }

    // Breathing animation
    if (s == '1') {
      int currBrightness = brightness;

      // Way up
      for (int j = 16; j < 200; j++) {
        if (j % 4 == 0) {
          currBrightness += 1;
          strip.setBrightness(currBrightness);
        }
        else {
          for (uint16_t i = 0; i < strip.numPixels(); i++) {
            strip.setPixelColor(i, strip.Color(j, j, j));
          }
          if (interrupt == true) {
            break;
          }
          strip.show();
          delay(16);
        }
      }

      // Avoid going in this loop if the previous one was break;
      if (!interrupt) {

        // Way down
        for (int j = 200; j > 16; j--) {

          if (j % 4 == 0) {
            currBrightness -= 1;
            strip.setBrightness(currBrightness);
          }
          else {
            for (uint16_t i = 0; i < strip.numPixels(); i++) {
              strip.setPixelColor(i, strip.Color(j, j, j));
            }

            if (interrupt == true) {
              interrupt = false;
              strip.setBrightness(brightness);
              animReset();
              break;
            }
            strip.show();
            delay(16);
          }
        }
      }

      //Clean up
      else {
        interrupt = false;
        strip.setBrightness(brightness);
        animReset();
      }
    }


    // Loading animation
    if (s == '2') {
      for (uint16_t i = 0; i < strip.numPixels(); i++) {
        strip.setPixelColor(i, strip.Color(255, 255, 255));
        strip.show();
        if (interrupt == true) {
          interrupt = false;
          animReset();
          break;
        }
        delay(120);
      }
    }

    // Hotword detected and listening to command
    else if (s == '3') {
      uint16_t i, j;
      for (j = 0; j < 256; j++) {
        //for(i=0; i< strip.numPixels(); i++) {     // Original code
        for (i = 0; i <= strip.numPixels(); i++) { // Attempt to reverse direction of rainbow from 17 to 0
          strip.setPixelColor(strip.numPixels() - i, BWheel(((i * 256 / strip.numPixels()) + j) & 255));
        }

        if (interrupt == true) {
          interrupt = false;
          animReset();
          break;
        }
        strip.show();
        delay(1);
      }
    }


    // Thinking  state
    else if (s == '4') {
      uint16_t i, j;
      for (j = 0; j < 256; j++) {
        for (i = 0; i <= strip.numPixels(); i++) {
          strip.setPixelColor(strip.numPixels() - i, RGBWheel(((i * 256 / strip.numPixels()) + j) & 255));
        }
        if (interrupt == true) {
          interrupt = false;
          animReset();
          break;
        }
        strip.show();
        delay(2);
      }
    }

    // Janet is speaking
    else if (s == '5') {
      uint16_t i, j;
      for (j = 0; j < 256; j++) {
        //for(i=0; i< strip.numPixels(); i++) {     // Original code
        for (i = 0; i <= strip.numPixels(); i++) { // Attempt to reverse direction of rainbow from 17 to 0
          strip.setPixelColor(strip.numPixels() - i, GWheel(((i * 256 / strip.numPixels()) + j) & 255));
        }
        if (interrupt == true) {
          interrupt = false;
          animReset();
          break;
        }
        strip.show();
        delay(1);
      }
    }

    // Error state
    else if (s == '6') {
      for (int j = 0; j < 5; j++) {
        for (uint16_t i = 0; i < strip.numPixels(); i++) {
          strip.setPixelColor(i, strip.Color(255, 0, 0));
        }

        if (interrupt == true) {
          interrupt = false;
          animReset();
          break;
        }
        strip.show();
        delay(120);
        for (uint16_t i = 0; i < strip.numPixels(); i++) {
          strip.setPixelColor(i, strip.Color(0, 0, 0));
        }

        if (interrupt == true) {
          interrupt = false;
          animReset();
          break;
        }

        strip.show();
        delay(120);
      }
    }
  }
}
void TaskSerial(void *pvParameters)  // This is a task.
{
  (void) pvParameters;

  for (;;)
  {
    if (Serial.available()) {
      char c = Serial.read();
      Serial.print("received new cmd : ");
      Serial.println(c);
      if (c == '0' || c == '1' || c == '2' || c == '3' || c == '4' || c == '5' || c == '6') {
        if (s != c) {
          s = c;
          interrupt = true;
        }
      }

      else if (c == '+') {
        if (brightness < 200) {
          brightness += 40;
          Serial.println(brightness);
          strip.setBrightness(brightness);
        }
      }

      else if (c == '-') {
        if (brightness > 20 ) {
          brightness -= 40;
          Serial.println(brightness);
          strip.setBrightness(brightness);
        }
      }
    }
  }
}
