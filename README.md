# Teensy GUI - Minimal

A minimal GUI application for controlling Teensy-based solenoid controllers. This application provides a graphical interface built with DearPyGUI for real-time control and monitoring of solenoid actuators through serial communication.

## Features

- Real-time solenoid control via serial communication
- PWM duty cycle adjustment
- Envelope editor for custom control profiles
- Audio stream handling and playback
- Device status monitoring
- Configuration management

## Prerequisites

- **Python 3.8+** (tested with Python 3.12)
- **Teensy board** with compatible firmware
- **Unix-like system** (Linux, macOS, WSL)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/fiorettimichael/teensy-gui-minimal.git
cd teensy-gui-minimal
```

### 2. Create a virtual environment (recommended)

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure serial port (if needed)

Edit `config.py` to set your Teensy's serial port:

```bash
nano config.py
```

Update the `serial_port` variable:
```python
serial_port = "/dev/ttyACM0"  # Update with your actual port
```

To find your Teensy's port:

```bash
ls /dev/tty* | grep -E "(ACM|USB)"
```

## Running the Application

### Basic Usage

```bash
python3 main.py
```

### With Virtual Environment

If you created a virtual environment, make sure it's activated:

```bash
source venv/bin/activate
python3 main.py
```

## Firmware

The application works with Teensy firmware located in `assets/firmware/`. Available firmware versions:
- SolenoidController2.0.c
- SolenoidController2.1.c
- SolenoidController2.2.c

To upload firmware to your Teensy board, use the Teensy Loader or Arduino IDE with Teensyduino installed.

## Troubleshooting

### Permission Denied on Serial Port

If you get a permission error when accessing the serial port:

```bash
sudo usermod -a -G dialout $USER
```

Then log out and log back in for the changes to take effect.

### Module Not Found Errors

Ensure all dependencies are installed:

```bash
pip install --upgrade -r requirements.txt
```

### Audio Issues

If you encounter audio-related errors, ensure your system has the necessary audio libraries:

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install portaudio19-dev python3-pyaudio
```

**macOS:**
```bash
brew install portaudio
```

### Cannot Find Teensy Device

List all USB devices to verify your Teensy is connected:

```bash
lsusb
ls -l /dev/tty*
```

## Project Structure

```
teensy-gui-minimal/
├── main.py                 # Application entry point
├── teensy_controller.py    # Teensy communication interface
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── gui/                   # GUI components
│   ├── viewport.py        # Main viewport setup
│   ├── control_panel.py   # Control interface
│   ├── device_panel.py    # Device status panel
│   ├── envelope_editor.py # Envelope editing interface
│   ├── sound_panel.py     # Audio controls
│   ├── stream_panel.py    # Stream visualization
│   └── test_panel.py      # Testing utilities
├── assets/                # Fonts and firmware
│   └── firmware/          # Teensy firmware files
├── recorder.py            # Audio recording utilities
└── stream_handler.py      # Stream processing

```

## Dependencies

- `dearpygui==2.0.0` - GUI framework
- `pyserial==3.5` - Serial communication
- `sounddevice==0.5.2` - Audio input/output
- `soundfile==0.13.1` - Audio file handling
- `numpy==2.3.1` - Numerical processing
- `cffi==2.0.0` - C Foreign Function Interface

## License

See LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
