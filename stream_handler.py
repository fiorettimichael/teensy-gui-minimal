# === stream_handler.py ===
import os
import struct
import threading
import time
from datetime import datetime

class StreamHandler:
    def __init__(self, controller, binary_dir="stream_data", buffer_size=100000, sample_rate=None):
        self.controller = controller
        self.buffer_size = buffer_size
        self.duty_buffer = [0] * buffer_size
        self.current_buffer = [0] * buffer_size
        self.timestamps = [0.0] * buffer_size
        self.write_index = 0
        self.sample_count = 0
        self.lock = threading.Lock()
        self.streaming = False

        if sample_rate is None:
            try:
                status = controller.get_status()
                self.sample_rate = status.get("current_adc_rate", 10000.0)
            except Exception:
                self.sample_rate = 10000.0
        else:
            self.sample_rate = sample_rate

        os.makedirs(binary_dir, exist_ok=True)
        self.binary_filename = os.path.join(
            binary_dir, datetime.now().strftime("stream_%Y%m%d_%H%M%S.bin")
        )
        self.bin_file = open(self.binary_filename, "wb")

        self.header_written = False
        self.start_time = None
        self.thread = None

    def start(self):
        if self.streaming:
            return
        self.controller.start_streaming()
        self.streaming = True
        self.start_time = time.time()
        self.thread = threading.Thread(target=self._stream_loop, daemon=True)
        self.thread.start()

    def stop(self):
        if not self.streaming:
            return
        self.streaming = False
        try:
            self.controller.stop_streaming()
        except Exception as e:
            print(f"[Warning] stop_streaming ACK error: {e}")
        if self.bin_file:
            self.bin_file.close()
            self.bin_file = None

    def _write_header(self):
        header = struct.pack("<4sIfH", b"STRM", 2, self.sample_rate, 10)
        self.bin_file.write(header)
        self.header_written = True

    def _write_samples(self, samples, rel_time):
        if not self.header_written:
            self._write_header()
        for duty, current in samples:
            self.bin_file.write(struct.pack("<HHd", duty, current, rel_time))

    def _stream_loop(self):
        while self.streaming:
            pkt = self.controller.read_stream_packet(timeout=0.2)
            if pkt is None:
                continue
            typ, data = pkt
            if typ == "data":
                now = time.time() - self.start_time
                samples = data["samples"]
                with self.lock:
                    for duty, current in samples:
                        self.duty_buffer[self.write_index] = duty
                        self.current_buffer[self.write_index] = current
                        self.timestamps[self.write_index] = now
                        self.write_index = (self.write_index + 1) % self.buffer_size
                        self.sample_count += 1
                self._write_samples(samples, now)
            time.sleep(0.001)

    def export_csv(self, output_filename):
        import csv
        record_size = 12  # 2 bytes duty, 2 bytes current, 8 bytes timestamp
        header_size = 12  # 4sIfH
        with open(self.binary_filename, "rb") as f:
            header = f.read(header_size)
            if len(header) < header_size:
                raise ValueError("File too short for header")
            magic, version, sample_rate, bit_depth = struct.unpack("<4sIfH", header)
            if magic != b"STRM":
                raise ValueError("Invalid file header")
            with open(output_filename, "w", newline="") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(["timestamp", "duty", "current"])
                while True:
                    chunk = f.read(record_size)
                    if not chunk:
                        break
                    if len(chunk) < record_size:
                        # Print warning and skip incomplete record
                        print(f"[Warning] Incomplete record of {len(chunk)} bytes at end of file, skipping.")
                        break
                    try:
                        duty, current, t = struct.unpack("<HHd", chunk)
                        writer.writerow([t, duty, current])
                    except struct.error as e:
                        print(f"[Warning] Skipping corrupt record: {e}")
                        continue

    def get_recent_data(self, max_points):
        with self.lock:
            if self.sample_count < max_points:
                indices = list(range(self.sample_count))
            else:
                start = (self.write_index - max_points) % self.buffer_size
                indices = [(start + i) % self.buffer_size for i in range(max_points)]
            return (
                [self.timestamps[i] for i in indices],
                [self.duty_buffer[i] for i in indices],
                [self.current_buffer[i] for i in indices],
            )

    def get_last_timestamp(self):
        with self.lock:
            if self.sample_count == 0:
                return None
            idx = (self.write_index - 1) % self.buffer_size
            return self.timestamps[idx]

    def get_samples_by_time(self, t0, t1):
        with self.lock:
            if self.sample_count == 0:
                return [], [], []
            if self.sample_count < self.buffer_size:
                indices = list(range(self.sample_count))
            else:
                indices = [(self.write_index + i) % self.buffer_size for i in range(self.buffer_size)]
            ts = [self.timestamps[i] for i in indices]
            duty = [self.duty_buffer[i] for i in indices]
            current = [self.current_buffer[i] for i in indices]
            filtered = [(t, d, c) for t, d, c in zip(ts, duty, current) if t0 <= t <= t1]
            if not filtered:
                return [], [], []
            ts_f, d_f, c_f = zip(*filtered)
            return list(ts_f), list(d_f), list(c_f)