import math
import struct
import wave
import random

def generate_lofi_track(filename="lofi_track.wav", duration_sec=45, sample_rate=44100):
    num_samples = duration_sec * sample_rate
    num_channels = 2  # Stereo

    # Lo-fi BPM and timing (85 BPM = 0.7058 seconds per beat)
    bpm = 85
    beat_duration = 60.0 / bpm
    bar_duration = beat_duration * 4

    # Chord progression (Lo-fi jazz/R&B: Cmaj7 -> Am7 -> Fmaj7 -> G7)
    # Frequencies for notes
    C3, E3, G3, B3 = 130.81, 164.81, 196.00, 246.94
    A2, C3, E3, G3 = 110.00, 130.81, 164.81, 196.00
    F2, A2, C3, E3 = 87.31, 110.00, 130.81, 164.81
    G2, B2, D3, F3 = 98.00, 123.47, 146.83, 174.61

    chords = [
        [C3, E3, G3, B3],
        [A2, C3, E3, G3],
        [F2, A2, C3, E3],
        [G2, B2, D3, F3]
    ]

    audio_samples = []

    for i in range(num_samples):
        t = i / float(sample_rate)

        # Determine current bar and chord
        bar_index = int(t / bar_duration) % len(chords)
        chord_freqs = chords[bar_index]

        # 1. Soft Warm Synth Chords (sine waves with gentle envelope)
        t_in_bar = t % bar_duration
        envelope = math.exp(-0.8 * (t_in_bar % beat_duration))  # Gentle pulse

        chord_val = 0.0
        for freq in chord_freqs:
            # Low pass / warm sine + subtle detune shimmer
            chord_val += 0.15 * math.sin(2 * math.pi * freq * t) * envelope
            chord_val += 0.08 * math.sin(2 * math.pi * (freq * 1.002) * t) * envelope

        # 2. Upbeat Lo-fi Drum Beats (Kick on 1 & 3, Snare/Clap on 2 & 4, Hi-hat on 8ths)
        t_in_beat = t % beat_duration
        beat_num = int(t / beat_duration) % 4
        sub_beat = int((t % beat_duration) / (beat_duration / 2))  # 8th note division

        kick_val = 0.0
        snare_val = 0.0
        hihat_val = 0.0

        # Kick drum (frequency sweep from 120Hz down to 40Hz)
        if (beat_num == 0 or beat_num == 2 or (beat_num == 2 and sub_beat == 1)) and t_in_beat < 0.15:
            kick_env = math.exp(-30 * t_in_beat)
            freq_sweep = 120 * math.exp(-25 * t_in_beat) + 40
            kick_val = 0.35 * math.sin(2 * math.pi * freq_sweep * t_in_beat) * kick_env

        # Snare/Rimshot (noise burst + 180Hz body)
        if (beat_num == 1 or beat_num == 3) and t_in_beat < 0.12:
            snare_env = math.exp(-35 * t_in_beat)
            noise = (random.random() * 2.0 - 1.0) * 0.2
            body = math.sin(2 * math.pi * 180 * t_in_beat) * 0.2
            snare_val = (noise + body) * snare_env

        # Hi-hats (soft high-pass noise)
        t_in_8th = t % (beat_duration / 2)
        if t_in_8th < 0.04:
            hat_env = math.exp(-80 * t_in_8th)
            hihat_val = (random.random() * 2.0 - 1.0) * 0.06 * hat_env

        # 3. Ambient Vinyl Crackle (Lo-fi warmth)
        vinyl_val = 0.0
        if random.random() < 0.02:  # Occasional crackle pops
            vinyl_val = (random.random() * 2.0 - 1.0) * 0.04
        vinyl_hiss = (random.random() * 2.0 - 1.0) * 0.008

        # Combine channels (Left & Right with slight stereo width)
        left = chord_val + kick_val + snare_val + hihat_val + vinyl_val + vinyl_hiss
        right = chord_val * 0.9 + kick_val + snare_val + hihat_val * 0.8 + vinyl_val + vinyl_hiss

        # Clipping protection
        left = max(-0.95, min(0.95, left))
        right = max(-0.95, min(0.95, right))

        left_int = int(left * 32767)
        right_int = int(right * 32767)

        audio_samples.append(struct.pack('<hh', left_int, right_int))

    with wave.open(filename, 'wb') as wav_file:
        wav_file.setnchannels(num_channels)
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b''.join(audio_samples))

    print(f"Generated upbeat lo-fi track: {filename} ({duration_sec} seconds)")

if __name__ == "__main__":
    generate_lofi_track()
