import RPi.GPIO as GPIO
import time
import paho.mqtt.client as mqtt
from picamera2 import Picamera2
from gpiozero import Servo
from RPLCD.i2c import CharLCD
import tensorflow as tf
import numpy as np
import bluetooth
import os
import wave

# ---------- CONFIG ----------
THINGSBOARD_HOST = "demo.thingsboard.io"
ACCESS_TOKEN = "YOUR_ACCESS_TOKEN"

GPIO.setmode(GPIO.BCM)

# Ultrasonic Sensor
TRIG = 23
ECHO = 24
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

# Servos
servo_feeder = Servo(17)
servo_door = Servo(27)

# PIR Motion Sensor
PIR_PIN = 22
GPIO.setup(PIR_PIN, GPIO.IN)

# LCD
lcd = CharLCD('PCF8574', 0x27)

# Camera Setup
picam2 = Picamera2()
picam2.configure(picam2.create_still_configuration(main={"size": (640, 480)}))
picam2.start()

# MQTT Client
client = mqtt.Client()
client.username_pw_set(ACCESS_TOKEN)
client.connect(THINGSBOARD_HOST, 1883, 60)
client.loop_start()

# ---------- Load Models ----------
yamnet = tf.lite.Interpreter(model_path="yamnet.tflite")
yamnet.allocate_tensors()

vggish = tf.lite.Interpreter(model_path="vggish.tflite")
vggish.allocate_tensors()

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
    folder = "snapshots"
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)
    picam2.capture_file(filepath)
    print(f"Image captured: {filepath}")

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

def listen_bluetooth_audio(filename="audio.wav", duration_sec=5, chunk_size=1024):
    server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    server_sock.bind(("", 1))
    server_sock.listen(1)
    print("Waiting for Bluetooth audio...")
    client_sock, address = server_sock.accept()
    print(f"Connected to {address}")

    audio_data = []
    start_time = time.time()
    while time.time() - start_time < duration_sec:
        data = client_sock.recv(chunk_size)
        if not data:
            break
        audio_data.extend(np.frombuffer(data, dtype=np.int16))

    client_sock.close()

    audio_array = np.array(audio_data, dtype=np.int16)
    
    # Save to WAV
    folder = "audio_captures"
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)
    with wave.open(filepath, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit audio
        wf.setframerate(16000)  # YAMNet expects 16 kHz
        wf.writeframes(audio_array.tobytes())
    
    print(f"Saved audio file: {filepath}")
    return audio_array.astype(np.float32)

def detect_sound_class(audio_data):
    input_details = yamnet.get_input_details()
    output_details = yamnet.get_output_details()
    waveform = np.expand_dims(audio_data, axis=0)
    yamnet.set_tensor(input_details[0]['index'], waveform)
    yamnet.invoke()
    predictions = yamnet.get_tensor(output_details[0]['index'])[0]
    label_index = np.argmax(predictions)
    return label_index

def detect_emotion(audio_data):
    """
    Rule-based mapping from VGGish embeddings to emotions.
    """
    input_details = vggish.get_input_details()
    output_details = vggish.get_output_details()

    vggish.set_tensor(input_details[0]['index'], np.expand_dims(audio_data, 0).astype(np.float32))
    vggish.invoke()
    embedding = vggish.get_tensor(output_details[0]['index'])[0]

    # Simple heuristic mapping
    mean_val = np.mean(embedding)
    max_val = np.max(embedding)

    if mean_val > 0.1:
        return "Happy"
    elif mean_val < -0.1:
        return "Angry"
    elif max_val > 0.3:
        return "Hungry"
    else:
        return "Anxious"

# ---------- Main Loop ----------
try:
    print("Smart Pet Care System Started")
    while True:
        # PIR Motion Detection
        if GPIO.input(PIR_PIN):
            print("Motion detected near danger zone!")
            lcd.clear()
            lcd.write_string("Motion detected!")
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            capture_image(f"motion_{timestamp}.jpg")
            time.sleep(5)

        # Audio Detection
        lcd.clear()
        lcd.write_string("Listening...")
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        audio_data = listen_bluetooth_audio(filename=f"audio_{timestamp}.wav")

        sound_idx = detect_sound_class(audio_data)
        sound_map = {0: "bark", 1: "meow", 2: "whine", 3: "growl"}
        sound = sound_map.get(sound_idx, "unknown")

        emotion = detect_emotion(audio_data)
        lcd.clear()
        lcd.write_string(f"{sound} - {emotion}")
        print(f"Sound: {sound} | Emotion: {emotion}")

        # Action Based on Emotion
        if emotion == "Hungry":
            feed_pet()
        elif emotion in ["Angry", "Anxious"]:
            close_door()
            capture_image(f"alert_{time.strftime('%H%M%S')}.jpg")
        else:
            print("Pet is calm and happy.")

        # Send Data to ThingsBoard
        distance = measure_distance()
        telemetry = {
            "sound": sound,
            "emotion": emotion,
            "food_level_cm": distance,
            "motion_detected": bool(GPIO.input(PIR_PIN)),
            "door_state": "closed" if emotion in ["Angry", "Anxious"] else "open"
        }
        client.publish('v1/devices/me/telemetry', str(telemetry))
        print("Sent data to ThingsBoard:", telemetry)
        time.sleep(5)

except KeyboardInterrupt:
    GPIO.cleanup()
    client.loop_stop()
    print("System stopped safely.")
