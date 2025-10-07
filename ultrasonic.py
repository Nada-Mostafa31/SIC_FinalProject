import RPi.GPIO as GPIO 
import time 
import paho.mqtt.client as paho

TRIG = 23
ECHO = 24
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)


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


def on_connect(client, userdata, flags, rc):
    print("CONNACK received with " + str(rc))  ##CONNACK --> Connection Acknowledgment. A type of message predifiendned in MQTT protocol, the broker sends back to the client after the client sends a CONNECT message to the broker.

def on_publish(client, userdata, mid):   #mid --> message id
	print("connected")    

client = paho.Client()
client.username_pw_set("BasmalaEhab","B@s2442004")
client.tls_set()                         #enable TLS for secure connection

client.on_connect = on_connect
client.on_publish = on_publish

client.connect("12e3c1c15bdd48368787154aef22a377.s1.eu.hivemq.cloud", 8883)     #connect to broker
client.loop_start()


            
while True:
    distance = measure_distance()  
    print(f"Distance: {distance:.1f} cm")
    (rc, mid) = client.publish("sensor/distance", distance, qos=1)  
    time.sleep(2)



