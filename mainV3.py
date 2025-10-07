import RPi.GPIO as GPIO
import time
from gpiozero import Servo
from RPLCD.i2c import CharLCD
from picamera2 import Picamera2
import numpy as np
import socket
import tflite_runtime.interpreter as tflite
import os
import paho.mqtt.client as mqtt

# ---------- CONFIG ----------
THINGSBOARD_HOST = "demo.thingsboard.io"
ACCESS_TOKEN = "YOUR_ACCESS_TOKEN"

GPIO.setmode(GPIO.BCM)

# Ultrasonic Sensor
TRIG = 23
ECHO = 24
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

# PIR Sensor
PIR_PIN = 22
GPIO.setup(PIR_PIN, GPIO.IN)

# Servos
servo_feeder = Servo(17)
servo_door = Servo(27)

# LCD
lcd = CharLCD('PCF8574', 0x27)

# Camera
picam2 = Picamera2()
picam2.configure(picam2.create_still_configuration(main={"size": (640,480)}))
picam2.start()

# MQTT Client
client = mqtt.Client()
client.username_pw_set(ACCESS_TOKEN)
client.connect(THINGSBOARD_HOST, 1883, 60)
client.loop_start()

# Load TFLite models
yamnet = tflite.Interpreter(model_path="yamnet.tflite")
yamnet.allocate_tensors()
vggish = tflite.Interpreter(model_path="vggish.tflite")
vggish.allocate_tensors()
emotion_model = tflite.Interpreter(model_path="pet_emotion_model.tflite")
emotion_model.allocate_tensors()

# ---------- HELPER FUNCTIONS ----------

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
    folder = "snapshots"
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)
    picam2.capture_file(filepath)
    print(f"[📸] Image captured: {filepath}")

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
    waveform = np.expand_dims(audio_data, axis=0).astype(np.float32)
    input_details = yamnet.get_input_details()
    output_details = yamnet.get_output_details()
    yamnet.set_tensor(input_details[0]['index'], waveform)
    yamnet.invoke()
    predictions = yamnet.get_tensor(output_details[0]['index'])[0]
    label_index = np.argmax(predictions)
    return label_index

def detect_emotion(audio_data):
    waveform = np.expand_dims(audio_data, axis=0).astype(np.float32)
    # VGGish embedding
    v_input = vggish.get_input_details()
    v_output = vggish.get_output_details()
    vggish.set_tensor(v_input[0]['index'], waveform)
    vggish.invoke()
    embedding = vggish.get_tensor(v_output[0]['index'])[0]

    # Emotion classifier
    e_input = emotion_model.get_input_details()
    e_output = emotion_model.get_output_details()
    emotion_model.set_tensor(e_input[0]['index'], np.expand_dims(embedding, axis=0).astype(np.float32))
    emotion_model.invoke()
    pred = emotion_model.get_tensor(e_output[0]['index'])[0]
    emotions = ['Happy','Angry','Anxious','Hungry']
    return emotions[np.argmax(pred)]

# ---------- Audio Streaming ----------
def listen_wifi_audio(PORT=50007):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", PORT))
    s.listen(1)
    print("[🔊] Waiting for phone audio stream...")
    conn, addr = s.accept()
    print(f"[✅] Connected: {addr}")
    audio_data = []
    try:
        while True:
            data = conn.recv(2048)
            if not data:
                break
            audio_data.extend(np.frombuffer(data, dtype=np.int16))
    finally:
        conn.close()
    return np.array(audio_data, dtype=np.float32)

# ---------- MAIN LOOP ----------
try:
    print("[🚀] Smart Pet Care System Started")
    while True:
        # PIR Motion
        if GPIO.input(PIR_PIN):
            print("[⚠️] Motion detected near danger zone!")
            lcd.clear()
            lcd.write_string("Motion detected!")
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            capture_image(f"motion_{timestamp}.jpg")
            time.sleep(5)

        # Audio Detection
        lcd.clear()
        lcd.write_string("Listening...")
        audio_data = listen_wifi_audio()

        sound_idx = detect_sound_class(audio_data)
        sound_map = {0:"bark",1:"meow",2:"whine",3:"growl"}
        sound = sound_map.get(sound_idx,"unknown")
        emotion = detect_emotion(audio_data)
        lcd.clear()
        lcd.write_string(f"{sound}-{emotion}")
        print(f"[🐾] Sound: {sound} | Emotion: {emotion}")

        # Actions
        if emotion=="Hungry":
            feed_pet()
        elif emotion in ["Angry","Anxious"]:
            close_door()
            capture_image(f"alert_{time.strftime('%H%M%S')}.jpg")

        # Send to ThingsBoard
        distance = measure_distance()
        telemetry = {
            "sound": sound,
            "emotion": emotion,
            "food_level_cm": distance,
            "motion_detected": bool(GPIO.input(PIR_PIN)),
            "door_state": "closed" if emotion in ["Angry","Anxious"] else "open"
        }
        client.publish('v1/devices/me/telemetry', str(telemetry))
        print("[🌐] Sent data to ThingsBoard:", telemetry)
        time.sleep(5)

except KeyboardInterrupt:
    GPIO.cleanup()
    client.loop_stop()
    print("System stopped safely.")
