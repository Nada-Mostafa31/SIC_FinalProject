import os
import time
from time import sleep
from PIL import Image
import numpy as np
import tflite_runtime.interpreter as tflite
from picamera2 import Picamera2

# ------------------------------
# Camera capture function
# ------------------------------
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

# ------------------------------
# Load MobileNet TFLite model
# ------------------------------
pet_model_path = "mobilenet_pet.tflite"  # path to your trained TFLite pet classifier
pet_interpreter = tflite.Interpreter(model_path=pet_model_path)
pet_interpreter.allocate_tensors()
pet_input_details = pet_interpreter.get_input_details()
pet_output_details = pet_interpreter.get_output_details()

# ------------------------------
# Pet detection function
# ------------------------------
def is_pet_in_image(image_path, threshold=0.5):
    img = Image.open(image_path).resize((224, 224))  # MobileNet input size
    input_data = np.expand_dims(np.array(img)/255.0, axis=0).astype(np.float32)
    pet_interpreter.set_tensor(pet_input_details[0]['index'], input_data)
    pet_interpreter.invoke()
    output_data = pet_interpreter.get_tensor(pet_output_details[0]['index'])

    # Flatten the output to a 1D array
    output_data = np.array(output_data).flatten()
    
    # Assuming class 0 = pet
    pet_prob = output_data[0]
    return pet_prob > threshold

# ------------------------------
# Main test
# ------------------------------
if __name__ == "__main__":
    try:
        # Capture image
        image_path = capture_image_rpicam(filename=f"test_{int(time.time())}.jpg")
        
        # Check for pet
        if is_pet_in_image(image_path):
            print(f"? Pet detected in {image_path}")
        else:
            print(f"? No pet detected in {image_path}")
    except Exception as e:
        print(f"[ERROR] {e}")
