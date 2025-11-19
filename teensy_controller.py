import dearpygui.dearpygui as dpg
import serial
import struct
import time
import logging
from config import serial_port, baudrate
from gui.logger import log
from gui.device_panel import STATUS_BUTTON_TAG, STATUS_GROUP_TAG, on_status_pressed


# === Teensy Command IDs ===
CMD_PING = 0x01
CMD_GET_STATUS = 0x02
CMD_GET_DUTY = 0x03
CMD_STOP_PWM = 0x09
CMD_SET_PWM_OUTPUT_PIN = 0x10
CMD_SET_PWM_SENSING_PIN = 0x11
CMD_SET_CURRENT_SENSING_PIN = 0x12
CMD_SET_PWM_FREQ = 0x13
CMD_SET_PWM_ADC_RATE = 0x14
CMD_SET_CURRENT_ADC_RATE = 0x15
CMD_SET_PWM_ADC_RES = 0x16
CMD_SET_CURRENT_ADC_RES = 0x17
CMD_SET_PWM_DEPTH = 0x18
CMD_SET_DUTY_ACK = 0x19
CMD_SET_DUTY = 0x20
CMD_SET_DUTY_FAST = 0x21
CMD_SAVE_SETTINGS = 0x30
CMD_SOFT_RESET = 0x31
CMD_SOFT_RESET_SAVE = 0x32
CMD_ACK = 0x7F
CMD_START_STREAM = 0x40
CMD_STOP_STREAM = 0x41
CMD_SOFT_RELEASE = 0x60

# === Streaming constants ===
STREAM_PACKET_MAGIC = 0xA5
STREAM_TIME_MAGIC = 0xAA
STREAM_BUFFER_SIZE = 8

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TeensySolenoidController:
    def __init__(self, port=None):
        self.port = port or serial_port
        self.baudrate = baudrate
        self.ser = None
        self.is_connected = False

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            log.info("[Serial] Connection closed.")
            self.is_connected = False

            dpg.configure_item(STATUS_BUTTON_TAG, label="Unconnected",
                            callback=None, user_data=None)
            dpg.bind_item_theme(STATUS_BUTTON_TAG, "status_theme_disconnected")
            if dpg.does_item_exist(STATUS_GROUP_TAG):
                dpg.delete_item(STATUS_GROUP_TAG, children_only=False)

    def ping(self):
        log.info("[Serial] Pinging device...")
        self.send_command(CMD_PING)
        echoed_cmd = self.read_ack(expected_cmd=CMD_PING)
        # read_ack either raises or returns the echoed command ID
        if echoed_cmd != CMD_PING:
            self.close()
            raise Exception(f"[Serial] No valid response to PING (echoed={echoed_cmd})")
        log.info(f"[Serial] PING ACK received for cmd 0x{echoed_cmd:02X}")
        return True
    
    def stop_pwm(self):
        self.send_command(CMD_STOP_PWM)
        echoed_cmd = self.read_ack(expected_cmd=CMD_STOP_PWM)
        # read_ack either raises or returns the echoed command ID
        if echoed_cmd != CMD_STOP_PWM:
            self.close()
            raise Exception(f"[Serial] No valid response to CMD (echoed={echoed_cmd})")
        log.debug(f"[Serial] STOP ACK received for cmd 0x{echoed_cmd:02X}")
        log.info(f"[Serial] PWM Stopped")
        return True

    def connect(self, port=None):
        if port:
            self.port = port
        if not self.port:
            raise Exception("No serial port specified")
        
        try:
            dpg.configure_item(STATUS_BUTTON_TAG, label="Connecting...",  
                               callback=None,  
                               user_data=None)
            dpg.bind_item_theme(STATUS_BUTTON_TAG, "status_theme_connecting")
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            time.sleep(2)  # Let Teensy settle

            # Drain any garbage before sending commands
            junk = self.ser.read(self.ser.in_waiting or 1)
            if junk:
                log.debug(f"[Serial] Drained pre-connection bytes: {junk.hex(' ')}")

            self.ser.reset_input_buffer()

            self.ping()
            self.is_connected = True
            # Finally: show Connected
            dpg.configure_item(STATUS_BUTTON_TAG, label="Connected",
                               callback=lambda: on_status_pressed(self),
                               user_data=self)
            dpg.bind_item_theme(STATUS_BUTTON_TAG, "status_theme_connected")
        except Exception as e:
            log.error(f"Failed to connect: {e}")
            self.is_connected = False
            self.close()
            raise

    def _calculate_checksum(self, data: bytes) -> int:
        return sum(data) & 0xFF

    def send_command(self, cmd_id, payload=b''):
        if not self.ser or not self.ser.is_open:
            raise RuntimeError("Serial connection not established.")

        packet = bytes([cmd_id]) + payload
        length = len(packet)  # cmd_id + payload
        checksum = self._calculate_checksum(packet)
        full_packet = bytes([length]) + packet + bytes([checksum])

        self.ser.write(full_packet)
        log.debug(f"[Serial] Sent: cmd=0x{cmd_id:02X}, payload={payload.hex()}, checksum=0x{checksum:02X}")
        log.outgoing(f"{full_packet.hex(' ')}")


    def read_packet(self, retries=10, delay=0.01):
        for _ in range(retries):
            if self.ser.in_waiting >= 3:
                break
            time.sleep(delay)
        else:
            return None

        header = self.ser.read(2)
        if len(header) < 2:
            return None

        length, cmd_id = header
        if length > 64:
            raise Exception(f"[Serial] Invalid length byte: {length}")

        payload = self.ser.read(length - 1)
        if len(payload) < (length - 1):
            raise Exception("[Serial] Incomplete payload")

        time.sleep(0.005)  # let Teensy catch up
        checksum = self.ser.read(1)
        if len(checksum) < 1:
            raise Exception(f"[Serial] Missing checksum byte after payload: {payload.hex()}")

        data = bytes([cmd_id]) + payload
        if self._calculate_checksum(data) != checksum[0]:
            raise Exception("[Serial] Checksum mismatch")

        log.debug(f"[Serial] Received: cmd=0x{cmd_id:02X}, payload={payload.hex()}, checksum=0x{checksum[0]:02X}")
        full = bytes([length, cmd_id]) + payload + checksum
        log.incoming(" ".join(f"{b:02X}" for b in full))
        
        return cmd_id, payload


    def read_ack(self, expected_cmd=None):

        result = self.read_packet()
        if result is None:
            raise Exception("[Serial] No ACK received")

        cmd_id, payload = result
        if cmd_id != CMD_ACK:
            raise Exception(f"[Serial] Expected ACK, got {cmd_id:#02x}")

        if len(payload) < 1:
            raise Exception("[Serial] Malformed ACK packet")

        # Pull the echoed command *first*
        echoed_cmd = payload[0]

        # Now check it
        if expected_cmd is not None and echoed_cmd != expected_cmd:
            raise Exception(f"[Serial] Unexpected ACK for cmd {echoed_cmd:#02x}")

        return echoed_cmd

    def log_status_fields(self, payload):
        try:
            if len(payload) != 16:
                log.info(f"[Status] Invalid payload length: {len(payload)}")
                return

            (
                fw_major,
                fw_minor,
                pwm_output_pin,
                pwm_sensing_pin,
                current_sensing_pin,
                pwm_freq,
                pwm_adc_rate,
                current_adc_rate,
                pwm_adc_res,
                current_adc_res,
                pwm_depth
            ) = struct.unpack(">BBBBBIHHBBB", payload)

            log.info(f"[Status] Firmware Version: {fw_major}.{fw_minor}")
            log.info(f"[Status] PWM Output Pin: {pwm_output_pin}")
            log.info(f"[Status] PWM Sensing Pin: {pwm_sensing_pin}")
            log.info(f"[Status] Current Sensing Pin: {current_sensing_pin}")
            log.info(f"[Status] PWM Frequency: {pwm_freq} Hz")
            log.info(f"[Status] PWM ADC Rate: {pwm_adc_rate} Hz")
            log.info(f"[Status] Current ADC Rate: {current_adc_rate} Hz")
            log.info(f"[Status] PWM ADC Resolution: {pwm_adc_res} bits")
            log.info(f"[Status] Current ADC Resolution: {current_adc_res} bits")
            log.info(f"[Status] PWM Depth: {pwm_depth}")

        except Exception as e:
            log.info(f"[Status] Failed to parse payload: {e}")

    def get_status(self):
        self.send_command(CMD_GET_STATUS)
        result = self.read_packet()
        if not result or result[0] != CMD_GET_STATUS:
            raise Exception("[Serial] Invalid status response")

        payload = result[1]
        self.log_status_fields(payload)
        if len(payload) != 16:
            raise Exception("[Serial] Invalid status payload length")

        (
            fw_major,
            fw_minor,
            pwm_output_pin,
            pwm_sensing_pin,
            current_sensing_pin,
            pwm_freq,
            pwm_adc_rate,
            current_adc_rate,
            pwm_adc_res,
            current_adc_res,
            pwm_depth
        ) = struct.unpack(">BBBBBIHHBBB", payload)

        return {
            "firmware_version": f"{fw_major}.{fw_minor}",
            "pwm_output_pin": pwm_output_pin,
            "pwm_sensing_pin": pwm_sensing_pin,
            "current_sensing_pin": current_sensing_pin,
            "pwm_frequency": pwm_freq,
            "pwm_adc_rate": pwm_adc_rate,
            "current_adc_rate": current_adc_rate,
            "pwm_adc_resolution": pwm_adc_res,
            "current_adc_resolution": current_adc_res,
            "pwm_depth": pwm_depth
        }

    def get_duty(self):
        self.send_command(CMD_GET_DUTY)
        result = self.read_packet()
        if not result or result[0] != CMD_GET_DUTY or len(result[1]) != 2:
            raise Exception("[Serial] Invalid duty response")
        return struct.unpack(">H", result[1])[0]

    def set_pwm_frequency(self, frequency_hz):
        frequency_hz = int(frequency_hz)
        self.send_command(CMD_SET_PWM_FREQ, struct.pack(">I", frequency_hz))
        self.read_ack(expected_cmd=CMD_SET_PWM_FREQ)

    def set_pwm_output_pin(self, pin):
        self.send_command(CMD_SET_PWM_OUTPUT_PIN, struct.pack("B", pin))
        self.read_ack(expected_cmd=CMD_SET_PWM_OUTPUT_PIN)

    def set_pwm_sensing_pin(self, pin):
        self.send_command(CMD_SET_PWM_SENSING_PIN, struct.pack("B", pin))
        self.read_ack(expected_cmd=CMD_SET_PWM_SENSING_PIN)

    def set_current_sensing_pin(self, pin):
        self.send_command(CMD_SET_CURRENT_SENSING_PIN, struct.pack("B", pin))
        self.read_ack(expected_cmd=CMD_SET_CURRENT_SENSING_PIN)

    def set_pwm_adc_rate(self, rate_hz):
        self.send_command(CMD_SET_PWM_ADC_RATE, struct.pack(">H", rate_hz))
        self.read_ack(expected_cmd=CMD_SET_PWM_ADC_RATE)

    def set_current_adc_rate(self, rate_hz):
        self.send_command(CMD_SET_CURRENT_ADC_RATE, struct.pack(">H", rate_hz))
        self.read_ack(expected_cmd=CMD_SET_CURRENT_ADC_RATE)

    def set_pwm_adc_resolution(self, bits):
        self.send_command(CMD_SET_PWM_ADC_RES, struct.pack("B", bits))
        self.read_ack(expected_cmd=CMD_SET_PWM_ADC_RES)

    def set_current_adc_resolution(self, bits):
        self.send_command(CMD_SET_CURRENT_ADC_RES, struct.pack("B", bits))
        self.read_ack(expected_cmd=CMD_SET_CURRENT_ADC_RES)

    def set_pwm_depth(self, bits):
        self.send_command(CMD_SET_PWM_DEPTH, struct.pack("B", bits))
        self.read_ack(expected_cmd=CMD_SET_PWM_DEPTH)

    def set_duty(self, duty):
        self.send_command(CMD_SET_DUTY, struct.pack(">H", duty))

    def set_duty_ack(self, duty):
        self.send_command(CMD_SET_DUTY_ACK, struct.pack(">H", duty))
        self.read_ack(expected_cmd=CMD_SET_DUTY_ACK)

    def set_duty_fast(self, duty):
        self.send_command(CMD_SET_DUTY_FAST, struct.pack(">H", duty))

    def save_settings(self):
        self.send_command(CMD_SAVE_SETTINGS)
        self.read_ack(expected_cmd=CMD_SAVE_SETTINGS)

    def soft_reset(self):
        self.send_command(CMD_SOFT_RESET)

    def soft_reset_and_save(self):
        self.send_command(CMD_SOFT_RESET_SAVE)
        self.read_ack(expected_cmd=CMD_SOFT_RESET_SAVE)

    def start_streaming(self):
        """Send command to start streaming."""
        self.send_command(CMD_START_STREAM)
        self.read_ack(expected_cmd=CMD_START_STREAM)

    def stop_streaming(self):
        """Send command to stop streaming."""
        self.send_command(CMD_STOP_STREAM)
        # Flush serial buffer before reading ACK
        if self.ser:
            self.ser.reset_input_buffer()
        self.read_ack(expected_cmd=CMD_STOP_STREAM)

    def read_stream_packet(self, timeout=1.0):
        """
        Read a stream packet (data or time sync) from the serial port.
        Returns a tuple: (packet_type, data)
        packet_type: 'data' or 'time'
        data: dict with parsed fields
        """
        start_time = time.time()
        while True:
            if self.ser.in_waiting < 1:
                if (time.time() - start_time) > timeout:
                    return None
                time.sleep(0.001)
                continue

            magic = self.ser.read(1)
            if not magic:
                continue
            magic = magic[0]

            if magic == STREAM_PACKET_MAGIC:
                # Data packet: [A5][flags][8 samples * 4][crc]
                needed = 1 + 4 * STREAM_BUFFER_SIZE + 1
                rest = self.ser.read(needed)
                if len(rest) != needed:
                    continue
                flags = rest[0]
                samples = []
                for i in range(STREAM_BUFFER_SIZE):
                    base = 1 + 4 * i
                    duty = rest[base] | (rest[base + 1] << 8)
                    current = rest[base + 2] | (rest[base + 3] << 8)
                    samples.append((duty, current))
                crc = rest[-1]
                crc_data = bytes([flags]) + rest[1:-1]
                if self._compute_crc8(crc_data) != crc:
                    logger.warning("[Stream] CRC mismatch in data packet")
                    continue
                return ('data', {'flags': flags, 'samples': samples})

            elif magic == STREAM_TIME_MAGIC:
                # Time sync packet: [AA][type][4 bytes time][crc]
                rest = self.ser.read(1 + 4 + 1)
                if len(rest) != 6:
                    continue
                typ = rest[0]
                t_bytes = rest[1:5]
                t = int.from_bytes(t_bytes, 'big')
                crc = rest[5]
                crc_data = bytes([typ]) + t_bytes
                if self._compute_crc8(crc_data) != crc:
                    logger.warning("[Stream] CRC mismatch in time sync packet")
                    continue
                return ('time', {'type': typ, 'micros': t})

            else:
                # Not a stream packet, ignore or handle as needed
                continue


    def _compute_crc8(self, data):
        crc = 0x00
        for b in data:
            for _ in range(8):
                mix = (crc ^ b) & 0x01
                crc >>= 1
                if mix:
                    crc ^= 0x8C
                b >>= 1
        return crc

    def send_duty(self, percent):
        from config import inverting, pwm_depth
        if inverting:
            percent = 100.0 - percent
        scaled = int(round((percent / 100.0) * pwm_depth))
        self.set_duty(scaled)

    def send_duty_fast(self, percent):
        from config import inverting, pwm_depth
        if inverting:
            percent = 100.0 - percent
        scaled = int(round((percent / 100.0) * pwm_depth))
        self.set_duty_fast(scaled)

    def queue_traj_segment(self, start_percent, end_percent, duration_ms, shape=1):
        from config import pwm_depth
        start_val = int(round((start_percent / 100.0) * pwm_depth))
        end_val = int(round((end_percent / 100.0) * pwm_depth))
        duration_us = int(duration_ms * 1000)
        payload = (
            int(start_val).to_bytes(2, "big") +
            int(end_val).to_bytes(2, "big") +
            int(duration_us).to_bytes(2, "big") +
            bytes([shape])
        )
        self.send_command(0x52, payload)

    def start_automation(self):
        self.send_command(0x50)

    def send_soft_release(self, start_percent, n_steps, freq_hz, power_index):
        from config import pwm_depth
        start_val = int(round((start_percent / 100.0) * pwm_depth))
        payload = (
            int(start_val).to_bytes(2, "big") +
            int(n_steps).to_bytes(2, "big") +
            int(freq_hz).to_bytes(2, "big") +
            int(power_index).to_bytes(1, "big")
        )
        self.send_command(CMD_SOFT_RELEASE, payload)


