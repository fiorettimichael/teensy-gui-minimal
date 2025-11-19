import sounddevice as sd
import soundfile as sf

def record_audio(filepath, duration, sample_rate, channels, device, bit_depth):
    try:
        sd.default.device = device
        sd.default.samplerate = sample_rate
        sd.default.channels = channels
        dtype = bit_depth
        audio = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=channels, dtype=dtype)
        sd.wait()
        # Ensure correct subtype for float32
        subtype = None
        if dtype == "float32":
            subtype = "FLOAT"
        elif dtype == "int16":
            subtype = "PCM_16"
        elif dtype == "int24":
            subtype = "PCM_24"
        elif dtype == "int32":
            subtype = "PCM_32"
        # Write with explicit subtype if set
        if subtype:
            sf.write(filepath, audio, sample_rate, subtype=subtype)
        else:
            sf.write(filepath, audio, sample_rate)
    except Exception as e:
        print(f"[Recorder] Error: {e}")
