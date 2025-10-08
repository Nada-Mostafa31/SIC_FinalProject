from gpiozero import Servo, DistanceSensor
from time import sleep
import time 
import paho.mqtt.client as paho

# ================================
# Setup Section
# ================================

# Define GPIO pins (adjust as needed)
TRIG1 = 24
ECHO1 = 23
TRIG2 = 22
ECHO2 = 27
SERVO1_PIN = 18
SERVO2_PIN = 17

# Initialize sensors and servos
ultrasonic_food = DistanceSensor(echo=ECHO1, trigger=TRIG1, max_distance=1.0)
ultrasonic_door = DistanceSensor(echo=ECHO2, trigger=TRIG2, max_distance=1.0)
servo_food = Servo(SERVO1_PIN)
servo_door = Servo(SERVO2_PIN)

# ================================
# Servo Control Functions
# ================================
def on_connect(client, userdata, flags, rc):
    print("CONNACK received with " + str(rc))  ##CONNACK --> Connection Acknowl>

def on_publish(client, userdata, mid):   #mid --> message id
        print("connected")    

client = paho.Client()
client.username_pw_set("BasmalaEhab","B@s2442004")
client.tls_set()                         #enable TLS for secure connection

client.on_connect = on_connect
client.on_publish = on_publish

client.connect("12e3c1c15bdd48368787154aef22a377.s1.eu.hivemq.cloud", 8883) 
client.loop_start()


def open_servo(servo, name):
    """Open a servo (rotate to max position)."""
    servo.max()
    print(f"{name} opened")

def close_servo(servo, name):
    """Close a servo (rotate to min position)."""
    servo.min()
    print(f"{name} CLOSED")

# ================================
# Sensor Handling Functions
# ================================

def handle_ultrasonic_food():
    
    distance_cm = ultrasonic_food.distance * 100
    print(f"food sensor: {distance_cm:.2f} cm")
    capacity = (((30-distance_cm)/30)*100)
    (rc, mid) = client.publish("sensor/food", capacity , qos=1)  
	


def handle_ultrasonic_door():
    """Handle second ultrasonic sensor (for Servo 2)."""
    distance_cm = ultrasonic_door.distance * 100
    print(f"Ultrasonic_door Distance: {distance_cm:.2f} cm")

    if distance_cm >= 50:
        open_servo(servo_door, "Servo door")
    else:
        close_servo(servo_door, "Servo door")
    (rc, mid) = client.publish("sensor/door", "door closed" , qos=1)

def check_command(command):
    """
    Takes input (string) from another file.
    If command == 'hungry', open servo_food for 2 seconds, then close it.
    Otherwise, keep it closed.
    """
    if command.lower() == "hungry":
        open_servo(servo_food, "servo food")
        sleep(2)
        close_servo(servo_food, "servo food")
    else:
        close_servo(servo_food, "servo food")
# ================================
# Main Loop
# ================================

def main():
    print("System started. Monitoring both ultrasonic sensors...")
    try:
      while True:
       	handle_ultrasonic_food()
        handle_ultrasonic_door()
        print("-----------------------------")
        sleep(0.5)

        # Get user command
        user_input = input("Enter state: ")
        check_command(user_input)

    except KeyboardInterrupt:
     print("\nProgram stopped by user.")
     servo_food.detach()
     servo_door.detach()

# ================================
# Run the program
# ================================
if __name__ == "__main__":
    main()




