from gpiozero import Servo, DistanceSensor
from picamera2 import Picamera2
from time import sleep
import time
import json
import paho.mqtt.client as mqtt
import numpy as np
import os
import wave
from PIL import Image
import tflite_runtime.interpreter as tflite
from RPLCD.i2c import CharLCD  

# MQTT Setup

BROKER = "broker.hivemq.com"
PORT = 1883
USERNAME = None
PASSWORD = None

def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))

def on_publish(client, userdata, mid):
    print("Message published, mid:", mid)

client = mqtt.Client()
client.on_connect = on_connect
client.on_publish = on_publish

if USERNAME and PASSWORD:
    client.username_pw_set(USERNAME, PASSWORD)

client.connect(BROKER, PORT)
client.loop_start()


TRIG1, ECHO1 = 24, 23  # Food ultrasonic
TRIG2, ECHO2 = 22, 27  # Door ultrasonic
SERVO1_PIN, SERVO2_PIN = 18, 17

ultrasonic_food = DistanceSensor(echo=ECHO1, trigger=TRIG1, max_distance=1.0)
ultrasonic_door = DistanceSensor(echo=ECHO2, trigger=TRIG2, max_distance=1.0)
servo_food = Servo(SERVO1_PIN)
servo_door = Servo(SERVO2_PIN)


# LCD Setup (I2C)

try:
    lcd = CharLCD('PCF8574', 0x27) 
    lcd.clear()
    lcd.write_string(" Pet Care Booting")
    sleep(2)
    lcd.clear()
except Exception as e:
    lcd = None
    print("[LCD] Not detected. Running without display:", e)


# Load AI Models

print("Loading TFLite models...")

yamnet = tflite.Interpreter(model_path="yamnet.tflite")
yamnet.allocate_tensors()
yamnet_input = yamnet.get_input_details()
yamnet_output = yamnet.get_output_details()
YAMNET_INPUT_SIZE = yamnet_input[0]['shape'][0]

pet_model_path = "mobilenet_pet.tflite"
pet_interpreter = tflite.Interpreter(model_path=pet_model_path)
pet_interpreter.allocate_tensors()
pet_input = pet_interpreter.get_input_details()
pet_output = pet_interpreter.get_output_details()


def lcd_display(line1="", line2=""):
    """Display message on LCD if available."""
    if lcd:
        lcd.clear()
        lcd.write_string(line1[:16])
        lcd.crlf()
        lcd.write_string(line2[:16])

def capture_image(filename="snapshot.jpg"):
    folder = "snapshots"
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)

    picam2 = Picamera2()
    sleep(2)
    picam2.start()
    picam2.capture_file(filepath)
    picam2.stop()
    print(f"[CAMERA] Image captured: {filepath}")
    return filepath

def is_pet_in_image(image_path, threshold=0.5):
    img = Image.open(image_path).resize((224, 224))
    input_data = np.expand_dims(np.array(img) / 255.0, axis=0).astype(np.float32)
    pet_interpreter.set_tensor(pet_input[0]['index'], input_data)
    pet_interpreter.invoke()
    output = pet_interpreter.get_tensor(pet_output[0]['index'])
    pet_prob = np.array(output).flatten()[0]
    print(f"[AI] Pet probability: {pet_prob:.2f}")
    return pet_prob > threshold

def predict_sound_emotion(audio_path="received_audio.wav"):
    try:
        with wave.open(audio_path, 'rb') as wf:
            frames = wf.readframes(wf.getnframes())
            audio_data = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
        audio_data = audio_data / 32768.0

        preds = []
        for start in range(0, len(audio_data) - YAMNET_INPUT_SIZE + 1, YAMNET_INPUT_SIZE):
            chunk = audio_data[start:start + YAMNET_INPUT_SIZE]
            yamnet.set_tensor(yamnet_input[0]['index'], chunk.astype(np.float32))
            yamnet.invoke()
            preds.append(yamnet.get_tensor(yamnet_output[0]['index'])[0])

        if not preds:
            return "unknown"

        avg_preds = np.mean(preds, axis=0)
        label_index = np.argmax(avg_preds)
        sound_map = {0: "bark", 1: "meow", 2: "whine", 3: "growl"}
        sound = sound_map.get(label_index, "unknown")

        emotion = {"bark": "Hungry", "whine": "Anxious", "growl": "Angry"}.get(sound, "Happy")

        print(f"[YAMNET] Sound: {sound} | Emotion: {emotion}")
        return emotion
    except:
        return "unknown"

def open_servo(servo, name):
    servo.max()
    print(f"{name} opened")

def close_servo(servo, name):
    servo.min()
    print(f"{name} closed")

def feed_pet():
    open_servo(servo_food, "Food Servo")
    sleep(4)
    close_servo(servo_food, "Food Servo")


# Ultrasonic Handling

def handle_ultrasonic_food():
    distance_cm = ultrasonic_food.distance * 100
    capacity = max(0, min(((30 - distance_cm) / 30) * 100, 100))
    print(f"[FOOD] Distance: {distance_cm:.1f} cm | Capacity: {capacity:.1f}%")

    topic = "tb/sensors/Foodpot/data"
    payload = {"food_level": round(capacity, 1)}
    client.publish(topic, json.dumps(payload), qos=1)

    lcd_display("Food Level:", f"{capacity:.1f}%")

def handle_ultrasonic_door():
    distance_cm = ultrasonic_door.distance * 100
    print(f"[DOOR] Distance: {distance_cm:.1f} cm")

    if distance_cm < 50:
        print("[MOTION] Detected near door! Capturing image...")
        lcd_display("Motion Detected", "Checking...")
        img_path = capture_image(f"motion_{int(time.time())}.jpg")
        if is_pet_in_image(img_path):
            print("[PET] Pet detected near door. Closing door for safety.")
            lcd_display("Pet Detected", "Door Closed")
            close_servo(servo_door, "Door Servo")
        else:
            print("[ALERT] Unknown motion detected. Door stays open.")
            lcd_display("Unknown Motion", "Door Open")
            open_servo(servo_door, "Door Servo")

    topic = "tb/sensors/Door/data"
    payload = {"door_distance_cm": round(distance_cm, 1)}
    client.publish(topic, json.dumps(payload), qos=1)


# Main Loop

def main():
    print("Smart Pet Care System Started")
    lcd_display("Smart Pet Care", "System Started")
    sleep(2)

    try:
        while True:
            handle_ultrasonic_food()
            handle_ultrasonic_door()

            emotion = predict_sound_emotion()

            if emotion == "Hungry":
                lcd_display("Emotion:", "Hungry ")
                feed_pet()
            elif emotion in ["Angry", "Anxious"]:
                lcd_display("Emotion:", f"{emotio}⚠ ")
                close_servo(servo_door, "Door Servo")
                capture_image(f"alert_{int(time.time())}.jpg")
            else:
                lcd_display("Emotion:", f"{emotion} ")

            payload = {"emotion": emotion, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}
            client.publish("tb/sensors/Emotion/data", json.dumps(payload), qos=1)
            print("[MQTT] Published emotion data:", payload)

            print("-----------------------------------------")
            time.sleep(5)

    except KeyboardInterrupt:
        print("\nSystem stopped by user.")
        lcd_display("System", "Stopped")
        servo_food.detach()
        servo_door.detach()

if __name__ == "__main__":
    main()
