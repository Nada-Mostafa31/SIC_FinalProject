import socket, pickle, struct, wave

PORT = 5000
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind(('', PORT))
sock.listen(1)
print("🎧 Waiting for connection...")
conn, addr = sock.accept()
print(f"Connected by {addr}")

wf = wave.open("pet_sound.wav", 'wb')
wf.setnchannels(1)
wf.setsampwidth(2)
wf.setframerate(44100)

data = b""
payload_size = struct.calcsize("Q")

while True:
    while len(data) < payload_size:
        packet = conn.recv(4*1024)
        if not packet:
            break
        data += packet
    if not packet:
        break
    packed_msg_size = data[:payload_size]
    data = data[payload_size:]
    msg_size = struct.unpack("Q", packed_msg_size)[0]

    while len(data) < msg_size:
        data += conn.recv(4*1024)
    frame_data = data[:msg_size]
    data = data[msg_size:]
    frames = pickle.loads(frame_data)
    wf.writeframes(frames.tobytes())

wf.close()
conn.close()
sock.close()
print("Saved as pet_sound.wav")
