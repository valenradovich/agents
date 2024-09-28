import pyaudio
import numpy as np
from faster_whisper import WhisperModel
import time
from pynput import mouse
import wave
from datetime import datetime
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
    global is_listening
    if is_listening:
        # print("Audio callback called, is_listening:", is_listening)  # Debug print
        audio_queue.put(in_data)
    return (None, pyaudio.paContinue)

def process_audio(model):
    global is_listening
    # print("Processing audio, is_listening:", is_listening)  # Debug print
    buffer = []
    while not audio_queue.empty():
        buffer.extend(np.frombuffer(audio_queue.get(), dtype=np.float32))
    
    if buffer:
        # print(f"Buffer size: {len(buffer)}")  # Debug print
        audio_data = np.array(buffer)
        #save_audio(audio_data)
        
        if np.max(np.abs(audio_data)) < 0.01:
            print("Warning: Very low audio levels detected. Check your microphone.")
            return ""
        else:
            segments, info = model.transcribe(audio_data, beam_size=5)
            full_text = " ".join(segment.text for segment in segments)
            return full_text
    else:
        print("No audio data in buffer")  # Debug print
    
    return ""

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
    # print(f"Audio saved as {filename}")

# Add a function to toggle listening state
def toggle_listening(state):
    global is_listening
    is_listening = state
    #print(f"Listening state toggled to: {is_listening}")  # Debug print