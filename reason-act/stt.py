import pyaudio
import numpy as np
from faster_whisper import WhisperModel
import time
from pynput import mouse
import wave
from datetime import datetime
import threading
import queue
import os

# Global variables
audio_queue = queue.Queue()
is_listening = False
stop_thread = False

def initialize_whisper():
    model_size = "large-v3"
    return WhisperModel(model_size, device="cuda", compute_type="int8_float16")

def initialize_audio():
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paFloat32,
                    channels=1,
                    rate=16000,
                    input=True,
                    frames_per_buffer=1024,
                    stream_callback=audio_callback)
    stream.start_stream()
    return p, stream

def audio_callback(in_data, frame_count, time_info, status):
    if is_listening:
        audio_queue.put(in_data)
    return (None, pyaudio.paContinue)

def process_audio(model):
    buffer = []
    while not audio_queue.empty():
        buffer.extend(np.frombuffer(audio_queue.get(), dtype=np.float32))
    
    if buffer:
        audio_data = np.array(buffer)
        # save_audio(audio_data)
        
        if np.max(np.abs(audio_data)) < 0.01:
            print("Warning: Very low audio levels detected. Check your microphone.")
        else:
            segments, info = model.transcribe(audio_data, beam_size=5)
            for segment in segments:
                print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")

def on_click(x, y, button, pressed):
    global is_listening
    if button == mouse.Button.button9:
        is_listening = pressed
        if pressed:
            print("Listening...")
            audio_queue.queue.clear()
        else:
            print("Stopped listening.")
            process_audio(model)

def save_audio(audio_data, sample_rate=16000):
    if not os.path.exists("saved_audio"):
        os.makedirs("saved_audio")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"saved_audio/audio_{timestamp}.wav"
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes((audio_data * 32767).astype(np.int16).tobytes())
    print(f"Audio saved as {filename}")

def main():
    global stop_thread, model
    
    model = initialize_whisper()
    p, stream = initialize_audio()
    
    print("Ready. Press and hold the designated mouse button to start listening.")
    
    listener = mouse.Listener(on_click=on_click)
    listener.start()

    try:
        while not stop_thread:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Stopping...")
        stop_thread = True
    finally:
        listener.stop()
        stream.stop_stream()
        stream.close()
        p.terminate()

if __name__ == "__main__":
    main()