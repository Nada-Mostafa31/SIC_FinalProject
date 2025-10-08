import subprocess
import os

def capture_image_rpicam(filename="pet_snapshot.jpg"):
    folder = "snapshots"
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)
    
    # Capture image using libcamera-still (modern Pi OS)
    subprocess.run([
        "libcamera-still",
        "-o", filepath,
        "--width", "640",
        "--height", "480",
        "--nopreview"
    ])
    print(f"Image captured: {filepath}")
    return filepath
import tflite_runtime.interpreter as tflite
from PIL import Image
import numpy as np

# Load MobileNet TFLite
pet_model_path = "mobilenet_pet.tflite"  # your trained pet classifier
pet_interpreter = tflite.Interpreter(model_path=pet_model_path)
pet_interpreter.allocate_tensors()
pet_input_details = pet_interpreter.get_input_details()
pet_output_details = pet_interpreter.get_output_details()

def is_pet_in_image(image_path, threshold=0.5):
    img = Image.open(image_path).resize((224, 224))  # MobileNet input size
    input_data = np.expand_dims(np.array(img)/255.0, axis=0).astype(np.float32)
    pet_interpreter.set_tensor(pet_input_details[0]['index'], input_data)
    pet_interpreter.invoke()
    output_data = pet_interpreter.get_tensor(pet_output_details[0]['index'])[0]
    
    # Assuming class 0 = pet
    if output_data[0] > threshold:
        return True
    return False
import time

# Assuming you already imported your functions:
# from your_module import capture_image_rpicam, is_pet_in_image

# Take a snapshot
image_path = capture_image_rpicam(filename=f"test_{int(time.time())}.jpg")

# Check if a pet is in the image
if is_pet_in_image(image_path):
    print(f"✅ Pet detected in {image_path}")
else:
    print(f"❌ No pet detected in {image_path}")
