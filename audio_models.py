import numpy as np
import soundfile as sf
from tflite_runtime.interpreter import Interpreter

# ---------- Load TFLite Models ----------
yamnet = Interpreter(model_path="yamnet.tflite")
yamnet.allocate_tensors()

vggish = Interpreter(model_path="vggish.tflite")
vggish.allocate_tensors()

# ---------- Helper Functions ----------
def detect_sound_class(audio_data):
    input_details = yamnet.get_input_details()
    output_details = yamnet.get_output_details()

    waveform = np.expand_dims(audio_data, axis=0).astype(np.float32)
    yamnet.set_tensor(input_details[0]['index'], waveform)
    yamnet.invoke()

    predictions = yamnet.get_tensor(output_details[0]['index'])[0]
    label_index = np.argmax(predictions)

    sound_map = {0: "bark", 1: "meow", 2: "whine", 3: "growl"}
    return sound_map.get(label_index, "unknown")

def detect_emotion(audio_data):
    input_details = vggish.get_input_details()
    output_details = vggish.get_output_details()

    waveform = np.expand_dims(audio_data, axis=0).astype(np.float32)
    vggish.set_tensor(input_details[0]['index'], waveform)
    vggish.invoke()

    embedding = vggish.get_tensor(output_details[0]['index'])[0]

    # Simple heuristic for emotions
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

# ---------- Test Script ----------
if __name__ == "__main__":
    audio_file = "received_audio.wav"  # replace with your WAV file
    waveform, sr = sf.read(audio_file)

    if sr != 16000:
        print(f"Warning: expected 16 kHz sample rate, got {sr}")

    audio_data = waveform.astype(np.float32)

    sound = detect_sound_class(audio_data)
    emotion = detect_emotion(audio_data)

    print(f"Sound detected: {sound}")
    print(f"Emotion detected: {emotion}")
