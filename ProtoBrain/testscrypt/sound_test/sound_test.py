import pyaudio
import numpy as np

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

audio = pyaudio.PyAudio()

# Automatically pick USB mic by name
device_index = None
for i in range(audio.get_device_count()):
    dev = audio.get_device_info_by_index(i)
    if "usb" in dev["name"].lower():
        device_index = i
        break

if device_index is None:
    print("USB microphone not found!")
    print("Run: python3 -m pyaudio to list devices")
    exit()

print("Using device:", audio.get_device_info_by_index(device_index)["name"])

stream = audio.open(
    format=FORMAT,
    channels=CHANNELS,
    rate=RATE,
    input=True,
    input_device_index=device_index,
    frames_per_buffer=CHUNK
)

print("Listening... Ctrl+C to quit.")

try:
    while True:
        data = np.frombuffer(stream.read(CHUNK, exception_on_overflow=False), dtype=np.int16)
        volume = np.linalg.norm(data) / len(data)
        print(f"Volume: {volume:.4f}")
except KeyboardInterrupt:
    pass

stream.stop_stream()
stream.close()
audio.terminate()
