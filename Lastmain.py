import RPi.GPIO as GPIO
import time
from gpiozero import Servo
from RPLCD.i2c import CharLCD
import numpy as np
import socket
import tflite_runtime.interpreter as tflite
import os
import paho.mqtt.client as mqtt
import subprocess
from PIL import Image
import wave
from picamera2 import Picamera2
from time import sleep

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

# MQTT Client
client = mqtt.Client()
client.username_pw_set(ACCESS_TOKEN)
client.connect(THINGSBOARD_HOST, 1883, 60)
client.loop_start()

# Load YAMNet TFLite model
yamnet = tflite.Interpreter(model_path="yamnet.tflite")
yamnet.allocate_tensors()
input_details = yamnet.get_input_details()
output_details = yamnet.get_output_details()
input_size = input_details[0]['shape'][0]  # 15600

# Load MobileNet TFLite model for pet detection
pet_model_path = "mobilenet_pet.tflite"
pet_interpreter = tflite.Interpreter(model_path=pet_model_path)
pet_interpreter.allocate_tensors()
pet_input_details = pet_interpreter.get_input_details()
pet_output_details = pet_interpreter.get_output_details()

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

def capture_image_rpicam(filename="pet_snapshot.jpg"):
    folder = "snapshots"
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)

    picam2 = Picamera2()
    sleep(2)  # camera warm-up
    picam2.start()
    picam2.capture_file(filepath)
    picam2.stop()

    print(f"[CAMERA] Image captured: {filepath}")
    return filepath

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
    yamnet.set_tensor(input_details[0]['index'], waveform)
    yamnet.invoke()
    predictions = yamnet.get_tensor(output_details[0]['index'])[0]
    label_index = np.argmax(predictions)
    return label_index

def predict_chunk(wave_chunk):
    yamnet.set_tensor(input_details[0]['index'], wave_chunk.astype(np.float32))
    yamnet.invoke()
    preds = yamnet.get_tensor(output_details[0]['index'])[0]
    return preds

def is_pet_in_image(image_path, threshold=0.5):
    img = Image.open(image_path).resize((224, 224))
    input_data = np.expand_dims(np.array(img)/255.0, axis=0).astype(np.float32)
    pet_interpreter.set_tensor(pet_input_details[0]['index'], input_data)
    pet_interpreter.invoke()
    output_data = pet_interpreter.get_tensor(pet_output_details[0]['index'])
    output_data = np.array(output_data).flatten()  # Flatten to handle multi-element outputs
    pet_prob = output_data[0]  # Assuming class 0 = pet
    return pet_prob > threshold

# ---------- Audio Streaming ----------
filename = "received_audio.wav"
with wave.open(filename, 'rb') as wf:
    frames = wf.readframes(wf.getnframes())
    audio_data = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
audio_data = audio_data / 32768.0  # normalize to [-1,1]

# ---------- MAIN LOOP ----------
try:
    print("Smart Pet Care System Started")
    while True:
        # PIR Motion
        if GPIO.input(PIR_PIN):
            print("[⚠️] Motion detected near danger zone!")
            lcd.clear()
            lcd.write_string("Motion detected!")
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            image_path = capture_image_rpicam(f"motion_{timestamp}.jpg")

            # Check if pet is detected
            if is_pet_in_image(image_path):
                print("Pet detected! Closing door.")
                close_door()
                capture_image_rpicam(f"alert_{time.strftime('%H%M%S')}.jpg")
            else:
                print("Motion detected but it's not the pet. Door remains open.")
            time.sleep(5)

        # Audio Detection (YAMNet)
        step = input_size  # non-overlapping
        all_preds = []
        for start in range(0, len(audio_data) - input_size + 1, step):
            chunk = audio_data[start:start+input_size]
            all_preds.append(predict_chunk(chunk))

        if all_preds:
            avg_preds = np.mean(all_preds, axis=0)
            label_index = np.argmax(avg_preds)
        else:
            label_index = 0  # fallback

        sound_map = {0: "bark", 1: "meow", 2: "whine", 3: "growl"}
        sound = sound_map.get(label_index, "unknown")

        # Simple emotion rules
        if sound == "bark":
            emotion = "Hungry"
        elif sound == "whine":
            emotion = "Anxious"
        elif sound == "growl":
            emotion = "Angry"
        else:
            emotion = "Happy"

        print(f"Sound: {sound} | Emotion: {emotion}")

        # Actions based on emotion
        if emotion == "Hungry":
            feed_pet()
        elif emotion in ["Angry", "Anxious"]:
            close_door()
            capture_image_rpicam(f"alert_{time.strftime('%H%M%S')}.jpg")

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
        print("Sent data to ThingsBoard:", telemetry)
        time.sleep(5)

except KeyboardInterrupt:
    GPIO.cleanup()
    client.loop_stop()
    print("System stopped safely.")
