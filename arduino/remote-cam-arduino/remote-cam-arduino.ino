#include <Servo.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

#define TRIG 9
#define ECHO 11
#define SERVO 10

#define ST_ERR 2
#define ST_0 6
#define ST_1 5
#define ST_2 4
#define ST_3 3

long duration;
int distance;

Servo servo;
int pos = 180;

LiquidCrystal_I2C lcd(0x3F, 16, 2);

char* emptyline = "                ";

int curr_cmd = 0;
int flush_time = 200;
bool received = false;

int t_pos = 8;

void setup() {
  // put your setup code here, to run once:
  pinMode(TRIG, OUTPUT);
  pinMode(ECHO, INPUT);

  pinMode(ST_ERR, OUTPUT);
  pinMode(ST_0, OUTPUT);
  pinMode(ST_1, OUTPUT);
  pinMode(ST_2, OUTPUT);
  pinMode(ST_3, OUTPUT);

  Wire.begin();
  
  servo.attach(SERVO);
  servo.write(90);
  Serial.begin(115200);

  lcd.init();
  lcd.backlight();
  
}

void loop() {
  if (!received) {
    digitalWrite(ST_ERR, HIGH);
    if (Serial.available() > 0) {
      received = true;
      digitalWrite(ST_ERR, LOW);
      delay(2000);
      return;
    } else {
      return;
    }
  }
  switch (curr_cmd) {
    case 0:
      Serial.write(1);
      send_dist();
      curr_cmd++;
      break;
    case 1:
      Serial.write(2);
      curr_cmd++;
      break;
    case 2:
      Serial.write(4);
      send_pos();
      curr_cmd++;
      break;
    case 3:
      Serial.write(8);
      receive_pos();
      curr_cmd = 0;
      break;
  }

  Serial.flush();
}

void send_dist() {
  // Clears the trigPin
  digitalWrite(TRIG, LOW);
  delayMicroseconds(2);
  // Sets the trigPin on HIGH state for 10 micro seconds
  digitalWrite(TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG, LOW);
  // Reads the echoPin, returns the sound wave travel time in microseconds
  duration = pulseIn(ECHO, HIGH);
  // Calculating the distance
  distance= duration*0.034/2;

  lcd.setCursor(0, 0);
  lcd.print(emptyline);
  lcd.setCursor(0, 0);
  lcd.print(distance);
  lcd.print(" ");
  lcd.print(duration);
  Serial.write(distance);
}

void send_pos() {
  Serial.write(pos);
}

void receive_pos() {
  while (Serial.available() == 0) {
    continue;
  }
  pos = Serial.read();
  lcd.setCursor(0, 1);
  lcd.print(emptyline);
  lcd.setCursor(0, 1);
  lcd.print(pos);
  servo.write(pos);
}

