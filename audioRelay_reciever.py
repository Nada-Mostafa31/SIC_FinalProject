import socket
import numpy as np
import wave

UDP_IP = "0.0.0.0"   # listen on all interfaces
UDP_PORT = 5005

# Audio parameters
CHANNELS = 1
RATE = 16000
SAMPLE_WIDTH = 2  # bytes (16-bit)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
print("[Pi] Waiting for audio stream...")

frames = []

try:
    while True:
        data, addr = sock.recvfrom(4096)  # buffer size
        frames.append(data)
        print(f"[✅] Received {len(data)} bytes from {addr}")
except KeyboardInterrupt:
    print("[🛑] Stopping and saving audio...")

# Convert frames to a single bytes object
audio_bytes = b''.join(frames)

# Save as WAV
with wave.open("received_audio.wav", "wb") as wf:
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(SAMPLE_WIDTH)
    wf.setframerate(RATE)
    wf.writeframes(audio_bytes)

print("[💾] Audio saved as received_audio.wav")

