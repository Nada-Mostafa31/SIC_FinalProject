import numpy as np
import wave
from tflite_runtime.interpreter import Interpreter

# ---------- Load YAMNet TFLite ----------
yamnet = Interpreter(model_path="yamnet.tflite")
yamnet.allocate_tensors()
input_details = yamnet.get_input_details()
output_details = yamnet.get_output_details()
input_size = input_details[0]['shape'][0]  # 15600

# ---------- Load audio ----------
filename = "received_audio.wav"
with wave.open(filename, 'rb') as wf:
    frames = wf.readframes(wf.getnframes())
    audio_data = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
audio_data = audio_data / 32768.0  # normalize to [-1,1]

# ---------- Process in chunks ----------
def predict_chunk(wave_chunk):
    yamnet.set_tensor(input_details[0]['index'], wave_chunk.astype(np.float32))
    yamnet.invoke()
    preds = yamnet.get_tensor(output_details[0]['index'])[0]
    return preds

# Sliding window over audio
step = input_size  # non-overlapping
all_preds = []
for start in range(0, len(audio_data) - input_size + 1, step):
    chunk = audio_data[start:start+input_size]
    all_preds.append(predict_chunk(chunk))

# Average predictions
if all_preds:
    avg_preds = np.mean(all_preds, axis=0)
    label_index = np.argmax(avg_preds)
else:
    label_index = 0  # fallback

# Simple mapping
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
