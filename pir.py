from gpiozero import DigitalInputDevice
import time

# Initialize the IR sensor on GPIO pin 4 (change if using a different pin)
# pull_up=True for active-low sensors (LOW when object detected, e.g., TCRT5000)
ir_sensor = DigitalInputDevice(22, pull_up=True)

# Variables for debouncing
last_motion_time = 0
debounce_delay = 2  # Seconds to wait before detecting new motion

print("IR sensor is ready. Waiting for someone to pass by...")

# Allow sensor to stabilize
print("Warming up sensor for 5 seconds...")
time.sleep(5)

# Main loop to check for motion with debouncing
while True:
    current_time = time.time()
    
    # Check for motion (active-low: LOW means object detected)
    # Change to if ir_sensor.value if your sensor is active-high
    if not ir_sensor.value and (current_time - last_motion_time) > debounce_delay:
        print("Motion detected! Someone passed by.")
        last_motion_time = current_time  # Update last motion time
    
    # Small delay to prevent CPU overuse
    time.sleep(0.1)






