import RPi.GPIO as GPIO
import time
import paho.mqtt.client as mqtt
from picamera2 import Picamera2
import cv2
import tensorflow as tf
import numpy as np
import io
from gpiozero import Servo
from smbus2 import SMBus
from RPLCD.i2c import CharLCD
import bluetooth

# ---------- CONFIG ----------
THINGSBOARD_HOST = "demo.thingsboard.io"   # replace with your TB server
ACCESS_TOKEN = "YOUR_ACCESS_TOKEN"

GPIO.setmode(GPIO.BCM)

# Ultrasonic
TRIG = 23
ECHO = 24
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

# Servos
servo_feeder = Servo(17)
servo_door = Servo(27)

# LCD
lcd = CharLCD('PCF8574', 0x27)

# Camera
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"size": (640, 480)}))
picam2.start()

# MQTT Client
client = mqtt.Client()
client.username_pw_set(ACCESS_TOKEN)
client.connect(THINGSBOARD_HOST, 1883, 60)
client.loop_start()

# Load YAMNet model
interpreter = tf.lite.Interpreter(model_path="yamnet.tflite")
interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# ---------- Helper Functions ----------

def measure_distance():
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)
    start, stop = time.time(), time.time()
    while GPIO.input(ECHO) == 0:
        start = time.time()
    while GPIO.input(ECHO) == 1:
        stop = time.time()
    return (stop - start) * 34300 / 2

def capture_image(filename="pet_snapshot.jpg"):
    picam2.capture_file(filename)
    print("? Image captured:", filename)

def feed_pet():
    lcd.clear()
    lcd.write_string("Feeding pet...")
    servo_feeder.max()
    time.sleep(2)
    while measure_distance() > 8:
        time.sleep(0.5)
    servo_feeder.min()
    lcd.clear()
    lcd.write_string("Feeding done")

def close_door():
    lcd.clear()
    lcd.write_string("Closing door!")
    servo_door.min()
    time.sleep(2)
    servo_door.detach()

def detect_sound_class(audio_data):
    waveform = np.array(audio_data, dtype=np.float32)
    waveform = np.expand_dims(waveform, axis=0)
    interpreter.set_tensor(input_details[0]['index'], waveform)
    interpreter.invoke()
    predictions = interpreter.get_tensor(output_details[0]['index'])[0]
    label_index = np.argmax(predictions)
    return label_index

def listen_bluetooth_audio():
    server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    server_sock.bind(("", 1))
    server_sock.listen(1)
    print("? Waiting for Bluetooth audio stream...")
    client_sock, address = server_sock.accept()
    print(f"? Connected to {address}")
    audio_data = []
    while True:
        data = client_sock.recv(1024)
        if not data:
            break
        audio_data.extend(np.frombuffer(data, dtype=np.int16))
    client_sock.close()
    return audio_data

# ---------- Main Loop ----------

try:
    while True:
        lcd.clear()
        lcd.write_string("Listening...")
        audio_data = listen_bluetooth_audio()
        label_idx = detect_sound_class(audio_data)

        # Simplified sound mapping
        sound_map = {0: "bark", 1: "meow", 2: "whine", 3: "growl"}
        sound = sound_map.get(label_idx, "unknown")

        lcd.clear()
        lcd.write_string(f"Sound: {sound}")
        print("Detected sound:", sound)

        if sound in ["meow", "bark"]:
            feed_pet()
        elif sound in ["growl", "whine"]:
            capture_image()
            close_door()

        distance = measure_distance()
        telemetry = {
            "sound": sound,
            "food_level_cm": distance,
            "door_state": "closed" if sound in ["growl", "whine"] else "open"
        }
        client.publish('v1/devices/me/telemetry', str(telemetry))
        print("? Sent data to ThingsBoard:", telemetry)
        time.sleep(5)

except KeyboardInterrupt:
    GPIO.cleanup()
    client.loop_stop()
    print("System stopped")
