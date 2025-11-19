from datetime import datetime
import dearpygui.dearpygui as dpg

class DPGLogger:
    def __init__(self):
        self.LOG_LEVELS = {
            "info": True,
            "error": True,
            "debug": False
        }
        self.log_buffer = {
            "log_window": [],
            "debug_window": []
        }

    def create_log_panel(self):
        with dpg.group():
            dpg.add_text("Log Output")
            dpg.add_input_text(multiline=True, readonly=True, height=100, width=-1, tag="log_window")

    def create_debug_panel(self):
        with dpg.group():
            with dpg.group(horizontal=True):
                dpg.add_checkbox(label="Show Info", default_value=True,
                                 callback=lambda s, a, u: self.toggle_log_level("info", a))
                dpg.add_checkbox(label="Show Error", default_value=True,
                                 callback=lambda s, a, u: self.toggle_log_level("error", a))
                dpg.add_checkbox(label="Show Debug", default_value=False,
                                 callback=lambda s, a, u: self.toggle_log_level("debug", a))
            dpg.add_input_text(multiline=True, readonly=True, height=240, width=480, tag="debug_log")

    def toggle_log_level(self, level, enabled):
        self.LOG_LEVELS[level] = enabled

    def _log(self, message, level):
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_message = f"[{timestamp}] {message}"

        # Store in main log
        self.log_buffer["log_window"].append(full_message)
        dpg.set_value("log_window", "\n".join(self.log_buffer["log_window"][-100:]))

        # Store in debug log if enabled
        if self.LOG_LEVELS.get(level, False):
            debug_message = f"[{timestamp}] [{level.upper()}] {message}"
            self.log_buffer["debug_window"].append(debug_message)
            dpg.set_value("debug_log", "\n".join(self.log_buffer["debug_window"][-200:]))

    def info(self, message):
        self._log(message, "info")

    def error(self, message):
        self._log(message, "error")

    def debug(self, message):
        self._log(message, "debug")

    def create_packet_monitor(self):
        with dpg.group(horizontal=True):

            with dpg.child_window(width=350, height=200):
                dpg.add_text("<< Outgoing")
                dpg.add_input_text(multiline=True, readonly=True, tag="outgoing_log", height=170)

            with dpg.child_window(width=350, height=200):
                dpg.add_text(">> Incoming")
                dpg.add_input_text(multiline=True, readonly=True, tag="incoming_log", height=170)

        self.log_buffer["incoming_log"] = []
        self.log_buffer["outgoing_log"] = []

    def incoming(self, message):
        self.log_buffer["incoming_log"].append(message)
        dpg.set_value("incoming_log", "\n".join(self.log_buffer["incoming_log"][-200:]))

    def outgoing(self, message):
        self.log_buffer["outgoing_log"].append(message)
        dpg.set_value("outgoing_log", "\n".join(self.log_buffer["outgoing_log"][-200:]))


log = DPGLogger()

