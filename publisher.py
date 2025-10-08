import paho.mqtt.client as mqtt
import time
import random
import json

# HiveMQ broker connection
BROKER = "broker.hivemq.com"
PORT = 1883
USERNAME = None
PASSWORD = None

# MQTT callbacks
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))

def on_publish(client, userdata, mid):
    print("Message published, mid:", mid)

# Initialize client
client = mqtt.Client()
client.on_connect = on_connect
client.on_publish = on_publish

if USERNAME and PASSWORD:
    client.username_pw_set(USERNAME, PASSWORD)

client.connect(BROKER, PORT)
client.loop_start()

######################### Devices #########################
device_names = ["Foodpot", "Livingroom", "Door", "Window", "Kitchen"]

while True:
    for device in device_names:
        topic = f"tb/sensors/{device}/data" 

        # Build payload dynamically per device
        if device == "Foodpot":
            payload = {"food_level": round(random.uniform(0, 100), 1)}
        elif device in ["Livingroom", "Kitchen"]:
            payload = {"cat_present": random.choice([True, False])}
        elif device == "Door":
            payload = {"door_status": random.choice(["open", "closed"])}
        elif device == "Window":
            payload = {"window_status": random.choice(["open", "closed"])}

        # Publish telemetry
        client.publish(topic, json.dumps(payload), qos=1)
        print(f"Published to {topic}: {payload}")

        # Publish simple state for Node-RED
        topic_state = f"tb/sensors/State"
        payload_state = random.choice(["ON", "OFF"])
        client.publish(topic_state, payload_state, qos=1)
        print(f"Published to {topic_state}: {payload_state}")

    time.sleep(5)
