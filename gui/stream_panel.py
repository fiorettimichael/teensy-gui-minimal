
import dearpygui.dearpygui as dpg
from stream_handler import StreamHandler
import time

STREAM_PANEL_TAG = "stream_panel"
STREAM_BUTTON_TAG = "stream_toggle_button"
STREAM_PLOT_DUTY_TAG = "stream_plot_duty"
STREAM_LINE_DUTY_TAG = "stream_line_duty"
STREAM_PLOT_CURR_TAG = "stream_plot_curr"
STREAM_LINE_CURR_TAG = "stream_line_curr"
STREAM_STATUS_TAG = "stream_status_text"
STREAM_MODE_SELECTOR_TAG = "stream_mode_selector"
STREAM_SAVE_BUTTON_TAG = "stream_save_button"
STREAM_SAVE_PATH_TAG = "stream_save_path"

PLOT_WINDOW_SECONDS = 5.0

class StreamPanel:
    def __init__(self, controller):
        self.controller = controller
        try:
            status = controller.get_status()
            sample_rate = status.get("current_adc_rate", 1000.0)
        except Exception:
            sample_rate = 1000.0
        self.handler = StreamHandler(controller, sample_rate=sample_rate)
        self.plot_mode = "scrolling"
        self.last_update_time = 0

    def toggle_stream(self):
        if self.handler.streaming:
            self.handler.stop()
            dpg.configure_item(STREAM_BUTTON_TAG, label="Start Streaming")
            dpg.set_value(STREAM_STATUS_TAG, "Streaming stopped.")
        else:
            self.handler.start()
            dpg.configure_item(STREAM_BUTTON_TAG, label="Stop Streaming")
            dpg.set_value(STREAM_STATUS_TAG, "Streaming started.")

    def update_plot(self):
        now = self.handler.get_last_timestamp()
        if now is None:
            return

        viewport_width = dpg.get_item_rect_size(STREAM_PLOT_DUTY_TAG)[0] or 400
        max_points = max(100, int(viewport_width))

        mode = dpg.get_value(STREAM_MODE_SELECTOR_TAG)

        if mode == "scrolling":
            t0 = max(0, now - PLOT_WINDOW_SECONDS)
            ts, duty, curr = self.handler.get_samples_by_time(t0, now)
            ts, duty, curr = self._downsample(ts, duty, curr, max_points)
        elif mode == "resizing":
            ts, duty, curr = self.handler.get_samples_by_time(0, now)
            ts, duty, curr = self._downsample(ts, duty, curr, max_points)
        elif mode == "wrap":
            t0 = max(0, now - PLOT_WINDOW_SECONDS)
            ts, duty, curr = self.handler.get_samples_by_time(t0, now)
            ts = [(t % PLOT_WINDOW_SECONDS) for t in ts]
            ts, duty, curr = self._downsample(ts, duty, curr, max_points)
        else:
            ts, duty, curr = [], [], []

        dpg.set_value(STREAM_LINE_DUTY_TAG, [ts, duty])
        dpg.set_value(STREAM_LINE_CURR_TAG, [ts, curr])

    def _downsample(self, ts, ys1, ys2, max_points):
        stride = max(1, len(ts) // max_points)
        return ts[::stride], ys1[::stride], ys2[::stride]

    def save_to_csv(self):
        path = dpg.get_value(STREAM_SAVE_PATH_TAG)
        if not path:
            dpg.set_value(STREAM_STATUS_TAG, "Please specify a file path.")
            return
        try:
            self.handler.export_csv(path)
            dpg.set_value(STREAM_STATUS_TAG, f"Exported to {path}")
        except Exception as e:
            dpg.set_value(STREAM_STATUS_TAG, f"Export failed: {e}")

def create_stream_panel(controller):
    panel = StreamPanel(controller)
    with dpg.group(tag="stream_panel_group"):
        with dpg.group(horizontal=True):
            dpg.add_button(label="Read Data", tag=STREAM_BUTTON_TAG, callback=lambda: panel.toggle_stream())
            dpg.add_spacer(width=30)
            dpg.add_combo(["Scrolling", "Resizing", "Wrap"], default_value="Scrolling", tag=STREAM_MODE_SELECTOR_TAG, label="View Mode", width=150)
            dpg.add_spacer(width=30)
            dpg.add_input_text(label="CSV Save Path", tag=STREAM_SAVE_PATH_TAG, default_value="stream_export.csv", width=200)
            dpg.add_spacer(width=30)
            dpg.add_button(label="Save to CSV", tag=STREAM_SAVE_BUTTON_TAG, callback=lambda: panel.save_to_csv())
            dpg.add_text("", tag=STREAM_STATUS_TAG)
        with dpg.plot(label="PWM Duty", height=200, width=-1, tag=STREAM_PLOT_DUTY_TAG):
            dpg.add_plot_axis(dpg.mvXAxis, label="Time (s)")
            with dpg.plot_axis(dpg.mvYAxis, label="Duty"):
                dpg.add_line_series([], [], tag=STREAM_LINE_DUTY_TAG, label="Duty")
        with dpg.plot(label="Current", height=200, width=-1, tag=STREAM_PLOT_CURR_TAG):
            dpg.add_plot_axis(dpg.mvXAxis, label="Time (s)")
            with dpg.plot_axis(dpg.mvYAxis, label="Current"):
                dpg.add_line_series([], [], tag=STREAM_LINE_CURR_TAG, label="Current")

    def periodic_update():
        panel.update_plot()
        dpg.set_frame_callback(dpg.get_frame_count() + 1, periodic_update)

    dpg.set_frame_callback(dpg.get_frame_count() + 1, periodic_update)
    return panel


###############
###############
#OLD#
'''
import dearpygui.dearpygui as dpg
from stream_handler import StreamHandler  # Assuming StreamHandler is in its own file now
import time

STREAM_PANEL_TAG = "stream_panel"
STREAM_BUTTON_TAG = "stream_toggle_button"
STREAM_PLOT_TAG = "stream_plot"
STREAM_LINE_TAG = "stream_line"
STREAM_STATUS_TAG = "stream_status_text"
STREAM_MODE_SELECTOR_TAG = "stream_mode_selector"
STREAM_SAVE_BUTTON_TAG = "stream_save_button"
STREAM_SAVE_PATH_TAG = "stream_save_path"

PLOT_WINDOW_SECONDS = 5.0

class StreamPanel:
    def __init__(self, controller):
        self.controller = controller
        # Try to get sample rate from controller status
        try:
            status = controller.get_status()
            sample_rate = status.get("current_adc_rate", 1000.0)
        except Exception:
            sample_rate = 1000.0
        self.handler = StreamHandler(controller, sample_rate=sample_rate)
        self.plot_mode = "scrolling"
        self.last_update_time = 0

    def toggle_stream(self):
        if self.handler.streaming:
            self.handler.stop()
            dpg.configure_item(STREAM_BUTTON_TAG, label="Start Streaming")
            dpg.set_value(STREAM_STATUS_TAG, "Streaming stopped.")
        else:
            self.handler.start()
            dpg.configure_item(STREAM_BUTTON_TAG, label="Stop Streaming")
            dpg.set_value(STREAM_STATUS_TAG, "Streaming started.")

    def update_plot(self):
        now = self.handler.get_last_timestamp()
        if now is None:
            return

        viewport_width = dpg.get_item_rect_size(STREAM_PLOT_TAG)[0] or 400
        max_points = max(100, int(viewport_width))

        mode = dpg.get_value(STREAM_MODE_SELECTOR_TAG)

        if mode == "scrolling":
            t0 = max(0, now - PLOT_WINDOW_SECONDS)
            ts, ys = self.handler.get_samples_by_time(t0, now)
            ts, ys = self._downsample(ts, ys, max_points)
        elif mode == "resizing":
            ts, ys = self.handler.get_samples_by_time(0, now)
            ts, ys = self._downsample(ts, ys, max_points)
        elif mode == "wrap":
            t0 = max(0, now - PLOT_WINDOW_SECONDS)
            ts, ys = self.handler.get_samples_by_time(t0, now)
            ts = [(t % PLOT_WINDOW_SECONDS) for t in ts]
            ts, ys = self._downsample(ts, ys, max_points)
        else:
            ts, ys = [], []

        dpg.set_value(STREAM_LINE_TAG, [ts, ys])

    def _downsample(self, ts, ys, max_points):
        stride = max(1, len(ys) // max_points)
        return ts[::stride], ys[::stride]

    def save_to_csv(self):
        path = dpg.get_value(STREAM_SAVE_PATH_TAG)
        if not path:
            dpg.set_value(STREAM_STATUS_TAG, "Please specify a file path.")
            return
        try:
            self.handler.export_csv(path)
            dpg.set_value(STREAM_STATUS_TAG, f"Exported to {path}")
        except Exception as e:
            dpg.set_value(STREAM_STATUS_TAG, f"Export failed: {e}")

def create_stream_panel(controller):
    panel = StreamPanel(controller)
    with dpg.group(tag="stream_panel_group"):
        with dpg.group(horizontal=True):
            #dpg.add_text("Streaming Panel", color=(255,255,0))
            dpg.add_button(label="Read Data", tag=STREAM_BUTTON_TAG, callback=lambda: panel.toggle_stream())
            dpg.add_spacer(width=30)
            dpg.add_combo(["Scrolling", "Resizing", "Wrap"], default_value="Scrolling", tag=STREAM_MODE_SELECTOR_TAG, label="View Mode", width=150)
            dpg.add_spacer(width=30)
            dpg.add_input_text(label="CSV Save Path", tag=STREAM_SAVE_PATH_TAG, default_value="stream_export.csv", width=200)
            dpg.add_spacer(width=30)
            dpg.add_button(label="Save to CSV", tag=STREAM_SAVE_BUTTON_TAG, callback=lambda: panel.save_to_csv())
            dpg.add_text("", tag=STREAM_STATUS_TAG)
        with dpg.plot(label="Real-Time Data", height=-1, width=-1, tag=STREAM_PLOT_TAG):
            dpg.add_plot_axis(dpg.mvXAxis, label="Time (s)")
            with dpg.plot_axis(dpg.mvYAxis, label="Value"):
                dpg.add_line_series([], [], tag=STREAM_LINE_TAG, label="Current")

    def periodic_update():
        panel.update_plot()
        dpg.set_frame_callback(dpg.get_frame_count() + 1, periodic_update)

    dpg.set_frame_callback(dpg.get_frame_count() + 1, periodic_update)
    return panel
}
'''