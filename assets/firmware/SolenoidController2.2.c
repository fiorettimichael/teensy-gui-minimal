// === Teensy Solenoid Controller Firmware ===
// Version 2.0
// 13 Jul 2025
// ============================================

#include <Arduino.h>
#include <EEPROM.h>


// === VERSION ===
#define FIRMWARE_VERSION_MAJOR 2
#define FIRMWARE_VERSION_MINOR 1

// === EEPROM ===
#define SETTINGS_EEPROM_ADDR 0
#define SETTINGS_MAGIC      0xA5A5A5A5

// === GENERAL ===
#define CMD_PING               0x01
#define CMD_GET_STATUS         0x02
#define CMD_GET_DUTY           0x03
#define CMD_STOP_PWM           0x09
#define CMD_SET_PWM_OUTPUT_PIN 0x10
#define CMD_SET_PWM_SENSING_PIN 0x11
#define CMD_SET_CURRENT_SENSING_PIN 0x12
#define CMD_SET_PWM_FREQ       0x13
#define CMD_SET_PWM_ADC_RATE   0x14
#define CMD_SET_CURRENT_ADC_RATE 0x15
#define CMD_SET_PWM_ADC_RES    0x16
#define CMD_SET_CURRENT_ADC_RES 0x17
#define CMD_SET_PWM_DEPTH      0x18
#define CMD_SET_DUTY_ACK       0x19
#define CMD_SET_DUTY           0x20
#define CMD_SET_DUTY_FAST      0x21
#define CMD_SAVE_SETTINGS      0x30
#define CMD_SOFT_RESET         0x31
#define CMD_SOFT_RESET_SAVE    0x32
#define CMD_ACK                0x7F

// === ERROR CODES ===
#define ERR_INVALID_PAYLOAD    0xE1
#define ERR_INVALID_DUTY       0xE2
#define ERR_UNKNOWN_COMMAND    0xE3

// === STREAMING ===
#define CMD_START_STREAM     0x40
#define CMD_STOP_STREAM      0x41
#define STREAM_PACKET_MAGIC  0xA5
#define STREAM_TIME_MAGIC    0xAA
#define STREAM_BUFFER_SIZE   8

// === AUTOMATION ===
#define CMD_START_AUTOMATION 0x50
#define CMD_STOP_AUTOMATION  0x51
#define CMD_QUEUE_TRAJ_SEG   0x52
#define TRAJ_BUFFER_SIZE 16

//MONITOR - Debugging//
#define PROFILE_PIN 10




// === DATA & STRUCTS ===
uint16_t current_duty = 0;

struct Settings {
  uint8_t  pwm_output_pin;
  uint8_t  pwm_sensing_pin;
  uint8_t  current_sensing_pin;
  uint32_t pwm_frequency;
  uint16_t pwm_adc_rate;
  uint16_t current_adc_rate;
  uint8_t  pwm_adc_resolution;
  uint8_t  current_adc_resolution;
  uint8_t  pwm_depth;
  uint32_t settings_version; // magic
};

struct SamplePair {
  uint16_t duty;
  uint16_t current;
};

struct TrajectorySegment {
  uint16_t start;
  uint16_t end;
  uint16_t duration_us;
  uint8_t shape; // 0: step, 1: linear
};

// === GLOBAL STATE ===
Settings cfg;
volatile SamplePair stream_buffer[STREAM_BUFFER_SIZE];
volatile uint8_t stream_index = 0;

volatile bool stream_enabled = false;
volatile bool automation_enabled = false;

// Trajectory State
volatile TrajectorySegment traj_buffer[TRAJ_BUFFER_SIZE];
volatile uint8_t traj_head = 0, traj_tail = 0;
volatile uint32_t traj_step_count = 0;
volatile uint32_t traj_step_index = 0;
volatile int32_t traj_duty_accum = 0;
volatile uint16_t traj_start = 0, traj_end = 0;
volatile uint8_t traj_shape = 0;

elapsedMicros elapsedSinceSync;
IntervalTimer controlLoop;

// === PACKET BUFFER ===
#define MAX_PACKET_SIZE 64
uint8_t packetBuffer[MAX_PACKET_SIZE];

uint16_t sample_buffer[STREAM_BUFFER_SIZE];

// === FORWARD DECLARATIONS ===
void loadSettings();
void saveSettings();
void setDefaultSettings();
void handleCommand(uint8_t* data, uint8_t len);
void sendStatusPacket();
void softReset();
uint8_t computeChecksum(const uint8_t* data, uint8_t len);
uint8_t computeCRC8(const uint8_t *data, size_t len);
void sendError(uint8_t cmdId, uint8_t errorCode);
void sendAck(uint8_t originalCmd);
FASTRUN void controlISR();
inline void startNextSegment();
inline uint16_t computeNextDuty();
void sendStreamPacket();
void sendTimeSyncPacket();
void handleStreaming();
uint16_t toUInt16(const uint8_t* p);
uint32_t toUInt32(const uint8_t* p);


// === SETUP ===
void setup() {
  Serial.begin(115200);
  Serial.setTimeout(10);
  while (!Serial);          // wait for host
  loadSettings();

  pinMode(cfg.pwm_output_pin, OUTPUT);
  analogWriteResolution(cfg.pwm_depth);
  analogWriteFrequency(cfg.pwm_output_pin, cfg.pwm_frequency);
  analogReadResolution(cfg.pwm_adc_resolution);

  // Set current sensing pin to INPUT
  pinMode(cfg.current_sensing_pin, INPUT);
  pinMode(PROFILE_PIN, OUTPUT);

  current_duty = (1u << cfg.pwm_depth) - 1;
  digitalWrite(cfg.pwm_output_pin, 1);

  controlLoop.begin(controlISR, 1000000UL / cfg.current_adc_rate);
}

// === MAIN LOOP ===
void loop() {

  if (stream_enabled) sendStreamPacket();
  
  if (Serial.available() < 1) return;

  uint8_t len = Serial.read();
  if (len < 1 || len > MAX_PACKET_SIZE - 2) {
    // invalid, discard and resync
    return;
  }

  // wait for full payload + checksum
  while (Serial.available() < len + 1) ;

  // read payload bytes (cmd + data)
  for (uint8_t i = 0; i < len; i++) {
    packetBuffer[i] = Serial.read();
  }
  uint8_t receivedChecksum = Serial.read();

  // verify
  if (computeChecksum(packetBuffer, len) == receivedChecksum) {
    handleCommand(packetBuffer, len);
  } else {
    sendError(packetBuffer[0], ERR_INVALID_PAYLOAD);
  }
}



// === CONTROL ISR ===

FASTRUN void controlISR() {

  digitalWriteFast(PROFILE_PIN, HIGH);


  uint16_t next_duty = automation_enabled ? computeNextDuty() : traj_end;
  analogWrite(cfg.pwm_output_pin, next_duty);
  uint16_t current = analogRead(cfg.current_sensing_pin);

  stream_buffer[stream_index].duty = next_duty;
  stream_buffer[stream_index].current = current;
  stream_index++;
  if (stream_index >= STREAM_BUFFER_SIZE) stream_index = 0;

  digitalWriteFast(PROFILE_PIN, LOW);


}

// === AUTOMATION ===

inline void startNextSegment() {
  if (traj_head == traj_tail) {
    automation_enabled = false;
    return;
  }
  TrajectorySegment seg;
  seg.start = traj_buffer[traj_tail].start;
  seg.end = traj_buffer[traj_tail].end;
  seg.duration_us = traj_buffer[traj_tail].duration_us;
  seg.shape = traj_buffer[traj_tail].shape;
  traj_tail = (traj_tail + 1) % TRAJ_BUFFER_SIZE;

  traj_start = seg.start;
  traj_end = seg.end;
  traj_shape = seg.shape;
  traj_step_count = seg.duration_us / (1000000UL / cfg.current_adc_rate);
  traj_step_index = 0;
  traj_duty_accum = 0;
}

inline uint16_t computeNextDuty() {
  if (!automation_enabled || traj_step_index >= traj_step_count)
    return traj_end;

  if (traj_shape == 0) return traj_end; // step

  traj_duty_accum += (int32_t)(traj_end - traj_start);
  uint16_t val = traj_start + (traj_duty_accum / traj_step_count);
  traj_step_index++;

  if (traj_step_index >= traj_step_count) startNextSegment();
  return val;
}




// === COMMAND HANDLER ===
//=== MAIN HANDLER ===


void handleCommand(uint8_t* data, uint8_t len) {
  uint8_t cmd = data[0];
  uint8_t* p = &data[1];
  uint8_t l = len - 1;

  switch (cmd) {
    case CMD_PING:
      sendAck(CMD_PING);
      break;

    case CMD_GET_STATUS:
      sendStatusPacket();
      break;

    case CMD_GET_DUTY: {
      uint8_t resp[4] = {
        CMD_GET_DUTY,
        uint8_t(current_duty >> 8),
        uint8_t(current_duty & 0xFF),
        0
      };
      resp[3] = computeChecksum(resp, 3);
      Serial.write(resp, 4);
      break;
    }

    case CMD_SET_PWM_OUTPUT_PIN:
      if (l == 1) {
        cfg.pwm_output_pin = p[0];
        sendAck(CMD_SET_PWM_OUTPUT_PIN);
      } else sendError(cmd, ERR_INVALID_PAYLOAD);
      break;

    case CMD_SET_CURRENT_SENSING_PIN:
      if (l == 1) {
        cfg.current_sensing_pin = p[0];
        pinMode(cfg.current_sensing_pin, INPUT); // Set new pin to INPUT
        sendAck(CMD_SET_CURRENT_SENSING_PIN);
      } else sendError(cmd, ERR_INVALID_PAYLOAD);
      break;

    case CMD_SET_PWM_FREQ:
      if (l == 4) {
        uint32_t freq = toUInt32(p);
        if (freq < 1000) freq = 1000;
        if (freq > 100000) freq = 100000;
        cfg.pwm_frequency = freq;
        analogWriteFrequency(cfg.pwm_output_pin, freq);
        sendAck(CMD_SET_PWM_FREQ);
      } else sendError(cmd, ERR_INVALID_PAYLOAD);
      break;


    case CMD_SET_DUTY_ACK:
      if (l == 2) {
        uint16_t d = toUInt16(p);
        uint16_t maxD = (1u << cfg.pwm_depth) - 1;
        if (d > maxD) sendError(cmd, ERR_INVALID_DUTY);
        else {
          current_duty = d;
          analogWrite(cfg.pwm_output_pin, d);
          sendAck(CMD_SET_DUTY_ACK);
        }
      } else sendError(cmd, ERR_INVALID_PAYLOAD);
      break;

    case CMD_SET_DUTY:
      if (l == 2) {
        uint16_t d = toUInt16(p);
        uint16_t maxD = (1u << cfg.pwm_depth) - 1;
        if (d > maxD) sendError(cmd, ERR_INVALID_DUTY);
        else {
          current_duty = d;
          analogWrite(cfg.pwm_output_pin, d);
        }
      } else sendError(cmd, ERR_INVALID_PAYLOAD);
      break;

    case CMD_SET_DUTY_FAST:
      if (l == 2) {
        uint16_t d = toUInt16(p);
        analogWrite(cfg.pwm_output_pin, d);
      }
      break;

    case CMD_STOP_PWM:
      pinMode(cfg.pwm_output_pin, OUTPUT);
      digitalWrite(cfg.pwm_output_pin, 1);
      sendAck(CMD_STOP_PWM);
      break;

    case CMD_START_STREAM:
      stream_enabled = true;  
      sendAck(CMD_START_STREAM);
      break;
      
    case CMD_STOP_STREAM:
      stream_enabled = false;
      sendAck(CMD_STOP_STREAM);
      break;
    
    case CMD_START_AUTOMATION:
      traj_head = traj_tail = 0;
      automation_enabled = true;
      startNextSegment();
      break;

    case CMD_STOP_AUTOMATION:
      automation_enabled = false;
      break;

    case CMD_QUEUE_TRAJ_SEG:
      if (len >= 8) {
        volatile TrajectorySegment& s = traj_buffer[traj_head];
        s.start = (p[0] << 8) | p[1];
        s.end = (p[2] << 8) | p[3];
        s.duration_us = (p[4] << 8) | p[5];
        s.shape = p[6];
        traj_head = (traj_head + 1) % TRAJ_BUFFER_SIZE;
      }

    case CMD_SAVE_SETTINGS:
      saveSettings();
      sendAck(CMD_SAVE_SETTINGS);
      break;

    case CMD_SOFT_RESET:
      softReset();
      break;

    case CMD_SOFT_RESET_SAVE:
      saveSettings();
      sendAck(CMD_SOFT_RESET_SAVE);
      delay(100);
      softReset();
      break;

    default:
      sendError(cmd, ERR_UNKNOWN_COMMAND);
      break;
  }
}

// === STREAMING HANDLER ===


void sendStreamPacket() {
  uint8_t packet[2 + 4 * STREAM_BUFFER_SIZE + 1];
  packet[0] = STREAM_PACKET_MAGIC;
  packet[1] = 0;

  noInterrupts();
  for (uint8_t i = 0; i < STREAM_BUFFER_SIZE; ++i) {
    packet[2 + 4 * i + 0] = stream_buffer[i].duty & 0xFF;
    packet[2 + 4 * i + 1] = stream_buffer[i].duty >> 8;
    packet[2 + 4 * i + 2] = stream_buffer[i].current & 0xFF;
    packet[2 + 4 * i + 3] = stream_buffer[i].current >> 8;
  }
  interrupts();

  packet[2 + 4 * STREAM_BUFFER_SIZE] = computeCRC8(&packet[1], 1 + 4 * STREAM_BUFFER_SIZE);
  Serial.write(packet, sizeof(packet));
}

void sendTimeSyncPacket() {
  uint32_t t = micros();
  uint8_t packet[1 + 1 + 4 + 1];
  packet[0] = STREAM_TIME_MAGIC;
  packet[1] = 0x01; // type
  packet[2] = (t >> 24) & 0xFF;
  packet[3] = (t >> 16) & 0xFF;
  packet[4] = (t >> 8) & 0xFF;
  packet[5] = t & 0xFF;
  packet[6] = computeCRC8(&packet[1], 5);
  Serial.write(packet, sizeof(packet));
}

void handleStreaming() {
  static uint32_t sample_interval_us = 0;
  static uint32_t last_sample_time = 0;
  static uint8_t sample_index = 0;
  static elapsedMillis sync_timer;

  if (!stream_enabled) return;

  // --- ADD THIS: If serial data is available, return so main loop can process it ---
  if (Serial.available() > 0) return;
  // -------------------------------------------------------------------------------

  if (sample_interval_us == 0) {
    sample_interval_us = 1000000UL / cfg.current_adc_rate;
    last_sample_time = micros();
  }

  uint32_t now = micros();
  if ((now - last_sample_time) >= sample_interval_us) {
    last_sample_time += sample_interval_us;
    sample_buffer[sample_index++] = analogRead(cfg.current_sensing_pin);
    if (sample_index >= STREAM_BUFFER_SIZE) {
      sendStreamPacket();
      sample_index = 0;
    }
  }

  if (sync_timer >= 500) {
    sendTimeSyncPacket();
    sync_timer = 0;
  }
}

// === ERROR RESPONSE ===
void sendError(uint8_t origCmd, uint8_t errcode) {
  // length=2 (errorID + code)
  uint8_t packet[4];
  packet[0] = 2;
  packet[1] = 0xFE;
  packet[2] = errcode;
  packet[3] = computeChecksum(&packet[1], 2);
  Serial.write(packet, 4);
}

// === STATUS PACKET ===
void sendStatusPacket() {
  uint8_t payload[16];
  uint8_t idx = 0;

  payload[idx++] = FIRMWARE_VERSION_MAJOR;
  payload[idx++] = FIRMWARE_VERSION_MINOR;
  payload[idx++] = cfg.pwm_output_pin;
  payload[idx++] = cfg.pwm_sensing_pin;
  payload[idx++] = cfg.current_sensing_pin;
  payload[idx++] = cfg.pwm_frequency >> 24;
  payload[idx++] = cfg.pwm_frequency >> 16;
  payload[idx++] = cfg.pwm_frequency >> 8;
  payload[idx++] = cfg.pwm_frequency;
  payload[idx++] = cfg.pwm_adc_rate >> 8;
  payload[idx++] = cfg.pwm_adc_rate;
  payload[idx++] = cfg.current_adc_rate >> 8;
  payload[idx++] = cfg.current_adc_rate;
  payload[idx++] = cfg.pwm_adc_resolution;
  payload[idx++] = cfg.current_adc_resolution;
  payload[idx++] = cfg.pwm_depth;

  uint8_t length = 1 + sizeof(payload);  // cmd + payload
  uint8_t cmd_id = CMD_GET_STATUS;

  Serial.write(length);
  Serial.write(cmd_id);
  Serial.write(payload, sizeof(payload));

  uint8_t chk_data[1 + sizeof(payload)];
  chk_data[0] = cmd_id;
  memcpy(&chk_data[1], payload, sizeof(payload));
  uint8_t chk = computeChecksum(chk_data, sizeof(chk_data));
  Serial.write(chk);
}

// === CHECKSUM ===
uint8_t computeChecksum(const uint8_t* data, uint8_t len) {
  uint8_t sum = 0;
  while (len--) sum += *data++;
  return sum;
}

// === CRC-8 ===
uint8_t computeCRC8(const uint8_t *data, size_t len) {
  uint8_t crc = 0x00;
  while (len--) {
    uint8_t inbyte = *data++;
    for (uint8_t i = 0; i < 8; i++) {
      uint8_t mix = (crc ^ inbyte) & 0x01;
      crc >>= 1;
      if (mix) crc ^= 0x8C;
      inbyte >>= 1;
    }
  }
  return crc;
}

// === ACK ===
void sendAck(uint8_t originalCmd) {
    // Length = 2 bytes: [ACK ID, echoed originalCmd]
    uint8_t packet[4];
    packet[0] = 2;               // number of bytes after this (ACK ID + echoedCmd)
    packet[1] = CMD_ACK;         // 0x7F
    packet[2] = originalCmd;     // the command we’re acknowledging
    packet[3] = computeChecksum(&packet[1], 2);  // checksum over packet[1] and packet[2]
    Serial.write(packet, 4);
}


// === SETTINGS MANAGEMENT ===
void loadSettings() {
  //EEPROM.get(SETTINGS_EEPROM_ADDR, cfg);
  //if (cfg.settings_version != SETTINGS_MAGIC) {
    setDefaultSettings();
   //saveSettings();
  //}
}

void saveSettings() {
  //cfg.settings_version = SETTINGS_MAGIC;
  //EEPROM.put(SETTINGS_EEPROM_ADDR, cfg);
}

void setDefaultSettings() {
  cfg.pwm_output_pin      = 5;
  cfg.pwm_sensing_pin     = A6;
  cfg.current_sensing_pin = A0;
  cfg.pwm_frequency       = 10000;
  cfg.pwm_adc_rate        = 10000;
  cfg.current_adc_rate    = 10000;
  cfg.pwm_adc_resolution  = 10;
  cfg.current_adc_resolution = 10;
  cfg.pwm_depth           = 10;
}


// === SOFT RESET ===
void softReset() {
  SCB_AIRCR = 0x05FA0004;
}


// === TYPE CONVERSION ===
uint16_t toUInt16(const uint8_t* p) {
  return (uint16_t(p[0]) << 8) | p[1];
}
uint32_t toUInt32(const uint8_t* p) {
  return (uint32_t(p[0]) << 24) | (uint32_t(p[1]) << 16)
       | (uint32_t(p[2]) << 8)  |  p[3];
}
