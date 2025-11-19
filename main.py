from teensy_controller import TeensySolenoidController
from gui.viewport import setup_gui

controller = TeensySolenoidController()

if __name__ == "__main__":
    setup_gui(controller)
