import dearpygui.dearpygui as dpg
from config import pwm_depth
import time
import numpy as np
import threading
from recorder import record_audio
import csv
import platform

SOFTWARE_VERSION = "2.1"  # Update as needed

device_connected = True
pwm_active = False
routine_running = False  # Add global flag

def show_no_device_popup():
    # If the popup exists and is shown, do nothing
    if dpg.does_item_exist("no_device_popup"):
        if dpg.is_item_shown("no_device_popup"):
            return
        else:
            dpg.delete_item("no_device_popup")
    # Create and show the popup
    
    with dpg.window(label="No Device Connected", modal=True, tag="no_device_popup",
                    no_title_bar=False, no_move=True, width=300, height=120):
        dpg.add_text("No device connected.")
        dpg.add_text("Select Device in Viewport > Device > Serial Port.")
        dpg.add_spacer(height=10)
        dpg.add_button(label="OK", width=100, callback=lambda: dpg.delete_item("no_device_popup"))

    # Center the popup in the viewport
    viewport_width = dpg.get_viewport_width()
    viewport_height = dpg.get_viewport_height()
    dpg.set_item_pos("no_device_popup", [viewport_width // 2 - 150, viewport_height // 2 - 60])


def is_controller_ready(controller):
    return controller and hasattr(controller, 'ser') and controller.ser and controller.ser.is_open

def on_stop(sender, app_data, controller):
    global routine_running
    routine_running = False
    if is_controller_ready(controller):
        controller.stop_pwm()
        controller.send_duty(0)
        dpg.set_value("test_progress", 0.0)
        update_button_states()
    else:
        show_no_device_popup()

def on_record_test_changed(sender, app_data):
    dpg.configure_item("recording_options_group", show=app_data)

def update_soft_release_duration_label():
    release_points = dpg.get_value("soft_release_points_field")
    freq = dpg.get_value("soft_release_freq_field")
    if freq > 0:
        duration = release_points / freq
        dpg.set_value("soft_release_duration_label", f"Approx. duration ~{duration*1000:.2f} ms")
    else:
        dpg.set_value("soft_release_duration_label", "Invalid")

def update_soft_release_duration_label_last():
    release_points = dpg.get_value("soft_release_points_field_last")
    freq = dpg.get_value("soft_release_freq_field_last")
    if freq > 0:
        duration = release_points / freq
        dpg.set_value("soft_release_duration_label_last", f"Approx. duration ~{duration*1000:.2f} ms")
    else:
        dpg.set_value("soft_release_duration_label_last", "Invalid")

def on_soft_release_param_changed(sender, app_data):
    update_soft_release_duration_label()

def on_soft_release_changed(sender, app_data):
    if app_data:
        dpg.configure_item("soft_release_options_group", show=app_data)
        update_soft_release_duration_label()
        dpg.configure_item("release_iterations_checkbox", show=app_data)
    else:
        dpg.configure_item("soft_release_options_group", show=False)
        dpg.set_value("test_release_parameters_checkbox", False)
        dpg.configure_item("release_iterations_checkbox", show=False)
        dpg.configure_item("release_iterations_group", show=False)
        dpg.set_value("soft_release_duration_label", "")
        dpg.set_value("soft_release_duration_label_last", "")

def on_soft_release_final_param_changed(sender, app_data):
    update_soft_release_duration_label_last()

def on_soft_release_test_changed(sender, app_data):
    if app_data:
        dpg.configure_item("release_iterations_group", show=app_data)
        update_soft_release_duration_label_last()
    else:
        dpg.configure_item("release_iterations_group", show=False)
        dpg.set_value("soft_release_duration_label_last", "")

def run_test_routine(controller):
    global routine_running
    routine_running = True
    # Read parameters from GUI
    start_duty_A = dpg.get_value("start_duty_value_A")
    start_time_A = dpg.get_value("start_duty_time_A")
    ramp_time_A = dpg.get_value("ramp_time_ms_A")
    end_duty_A = dpg.get_value("end_duty_value_A")
    end_time_A = dpg.get_value("end_duty_time_A")

    start_duty_B = dpg.get_value("start_duty_value_B")
    start_time_B = dpg.get_value("start_duty_time_B")
    ramp_time_B = dpg.get_value("ramp_time_ms_B")
    end_duty_B = dpg.get_value("end_duty_value_B")
    end_time_B = dpg.get_value("end_duty_time_B")

    steps = dpg.get_value("iterations")
    freq = dpg.get_value("rate")  # Hz

    soft_release_enabled = dpg.get_value("soft_release_checkbox")
    test_release_enabled = dpg.get_value("test_release_parameters_checkbox") if soft_release_enabled else False

    # Get first and last values for interpolation
    release_points_A = dpg.get_value("soft_release_points_field")
    release_freq_A = dpg.get_value("soft_release_freq_field")
    power_index_A = dpg.get_value("soft_release_power_field")

    if soft_release_enabled and test_release_enabled:
        release_points_B = dpg.get_value("soft_release_points_field_last")
        release_freq_B = dpg.get_value("soft_release_freq_field_last")
        power_index_B = dpg.get_value("soft_release_power_field_last")
    else:
        release_points_B = release_points_A
        release_freq_B = release_freq_A
        power_index_B = power_index_A

    # Interpolate parameters for each step
    start_duties = np.linspace(start_duty_A, start_duty_B, steps)
    start_times = np.linspace(start_time_A, start_time_B, steps)
    ramp_times = np.linspace(ramp_time_A, ramp_time_B, steps)
    end_duties = np.linspace(end_duty_A, end_duty_B, steps)
    end_times = np.linspace(end_time_A, end_time_B, steps)
    release_points_steps = np.linspace(release_points_A, release_points_B, steps)
    release_freq_steps = np.linspace(release_freq_A, release_freq_B, steps)
    power_index_steps = np.linspace(power_index_A, power_index_B, steps)

    # Check if all ramp times are zero
    if np.allclose(ramp_times, 0):
        # --- Software routine ---
        for i in range(steps):
            if not routine_running:
                controller.send_duty(0)
                break
            controller.send_duty(start_duties[i])
            dpg.set_value("test_progress", (i + 0.5) / steps)
            t0 = time.time()
            while routine_running and (time.time() - t0) < max(0, start_times[i]):
                time.sleep(0.01)
            if not routine_running:
                controller.send_duty(0)
                break
            controller.send_duty(end_duties[i])
            dpg.set_value("test_progress", (i + 1.0) / steps)
            t0 = time.time()
            while routine_running and (time.time() - t0) < max(0, end_times[i]):
                time.sleep(0.01)
            if not routine_running:
                controller.send_duty(0)
                break
            # --- Soft release after each step ---
            if soft_release_enabled:
                controller.send_soft_release(
                    end_duties[i],
                    int(round(release_points_steps[i])),
                    int(round(release_freq_steps[i])),
                    int(round(power_index_steps[i]))
                )
                if release_freq_steps[i] > 0:
                    time.sleep(release_points_steps[i] / release_freq_steps[i])
        controller.send_duty(0) 
    else:
        # --- Hardware trajectory routine ---
        for i in range(steps):
            if not routine_running:
                break
            controller.queue_traj_segment(start_duties[i], end_duties[i], ramp_times[i], shape=1)
            dpg.set_value("test_progress", (i + 1.0) / steps)
            # --- Soft release after each step ---
            if soft_release_enabled:
                controller.send_soft_release(
                    end_duties[i],
                    int(round(release_points_steps[i])),
                    int(round(release_freq_steps[i])),
                    int(round(power_index_steps[i]))
                )
                if release_freq_steps[i] > 0:
                    time.sleep(release_points_steps[i] / release_freq_steps[i])
        # Start automation
        controller.start_automation()
    dpg.set_value("test_progress", 0)
    routine_running = False

def run_test_routine_recorded(controller):
    global routine_running
    routine_running = True
    # Read parameters from GUI
    start_duty_A = dpg.get_value("start_duty_value_A")
    start_time_A = dpg.get_value("start_duty_time_A")
    ramp_time_A = dpg.get_value("ramp_time_ms_A")
    end_duty_A = dpg.get_value("end_duty_value_A")
    end_time_A = dpg.get_value("end_duty_time_A")
    start_duty_B = dpg.get_value("start_duty_value_B")
    start_time_B = dpg.get_value("start_duty_time_B")
    ramp_time_B = dpg.get_value("ramp_time_ms_B")
    end_duty_B = dpg.get_value("end_duty_value_B")
    end_time_B = dpg.get_value("end_duty_time_B")
    steps = dpg.get_value("iterations")
    freq = dpg.get_value("rate")  # Hz

    soft_release_enabled = dpg.get_value("soft_release_checkbox")
    test_release_enabled = dpg.get_value("test_release_parameters_checkbox") if soft_release_enabled else False
    export_csv = dpg.get_value("export_csv_checkbox")
    include_release = dpg.get_value("include_release_in_recording_checkbox")

    release_points_A = dpg.get_value("soft_release_points_field")
    release_freq_A = dpg.get_value("soft_release_freq_field")
    power_index_A = dpg.get_value("soft_release_power_field")

    if soft_release_enabled and test_release_enabled:
        release_points_B = dpg.get_value("soft_release_points_field_last")
        release_freq_B = dpg.get_value("soft_release_freq_field_last")
        power_index_B = dpg.get_value("soft_release_power_field_last")
    else:
        release_points_B = release_points_A
        release_freq_B = release_freq_A
        power_index_B = power_index_A

    # Recording parameters
    device = dpg.get_value("sound_device_combo")
    sample_rate = int(float(dpg.get_value("sample_rate_field")) * 1000)
    bit_depth = dpg.get_value("bit_depth_combo")
    channels = dpg.get_value("channel_count_field")
    folder = dpg.get_value("parent_folder_field")
    template = dpg.get_value("folder_template_field")
    note = dpg.get_value("note_field")
    pre_roll = dpg.get_value("pre_roll_field") / 1000.0
    post_roll = dpg.get_value("post_roll_field") / 1000.0

    # Get firmware version if possible
    try:
        fw_version = controller.get_status().get("firmware_version", "unknown")
    except Exception:
        fw_version = "unknown"

    # Get timestamp ONCE at the start
    import os, datetime
    now = datetime.datetime.now()
    date_str = now.strftime("%Y%m%d")
    time_str = now.strftime("%H%M")

    # Prepare first filename using the template and step 1 values
    velocity_1 = round(np.linspace(end_duty_A, end_duty_B, steps)[0], 2)
    take_1 = "1"
    # Fill all template fields, even if not used
    template_kwargs = dict(date=date_str, time=time_str, note=note, velocity=velocity_1, take=take_1)
    first_filepath = template.format(**template_kwargs)
    session_folder = os.path.join(folder, os.path.dirname(first_filepath))
    os.makedirs(session_folder, exist_ok=True)

    # Interpolate parameters for each step
    start_duties = np.linspace(start_duty_A, start_duty_B, steps)
    start_times = np.linspace(start_time_A, start_time_B, steps)
    ramp_times = np.linspace(ramp_time_A, ramp_time_B, steps)
    end_duties = np.linspace(end_duty_A, end_duty_B, steps)
    end_times = np.linspace(end_time_A, end_time_B, steps)
    release_points_steps = np.linspace(release_points_A, release_points_B, steps)
    release_freq_steps = np.linspace(release_freq_A, release_freq_B, steps)
    power_index_steps = np.linspace(power_index_A, power_index_B, steps)

    # Prepare CSV if needed
    csv_writer = None
    csv_file = None
    if export_csv:
        csv_path = os.path.join(session_folder, "session.csv")
        csv_file = open(csv_path, "w", newline="")
        csv_writer = csv.writer(csv_file)
        # Write CSV header as the first line
        csv_writer.writerow([
            "step", "start_hold_time", "start_duty", "ramp_time", "end_duty", "end_hold_time",
            "release_points", "switch_freq", "power_index"
        ])
        # Optionally, write metadata to a separate .txt file
        meta_path = os.path.join(session_folder, "session_meta.txt")
        with open(meta_path, "w") as meta_file:
            meta_file.write(f"Session timestamp: {date_str}_{time_str}\n")
            meta_file.write(f"Steps: {steps}\n")
            meta_file.write(f"Pre-roll: {pre_roll}s, Post-roll: {post_roll}s\n")
            meta_file.write(f"Sample rate: {sample_rate} Hz, Bit depth: {bit_depth}, Channels: {channels}\n")
            meta_file.write(f"Firmware version: {fw_version}, Software version: {SOFTWARE_VERSION}\n")
            meta_file.write(f"Platform: {platform.platform()}\n")
            meta_file.write(f"Note: {note}\n")

    if np.allclose(ramp_times, 0):
        # --- Software routine with per-step recording ---
        for i in range(steps):
            velocity = round(end_duties[i], 2)
            take = str(i+1)
            filename = template.format(date=date_str, time=time_str, note=note, velocity=velocity, take=take)
            filepath = os.path.join(folder, filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            # Calculate release duration if needed
            if soft_release_enabled:
                rel_points = int(round(release_points_steps[i]))
                rel_freq = int(round(release_freq_steps[i]))
                rel_power = int(round(power_index_steps[i]))
                release_duration = rel_points / rel_freq if rel_freq > 0 else 0
            else:
                rel_points = 1
                rel_freq = 0
                rel_power = 0
                release_duration = 0
            # Calculate total duration for recording
            duration = pre_roll + start_times[i] + end_times[i]
            if include_release:
                duration += release_duration
            duration += post_roll
            audio_thread = threading.Thread(
                target=record_audio,
                args=(filepath, duration, sample_rate, channels, device, bit_depth),
                daemon=True
            )
            audio_thread.start()
            time.sleep(pre_roll)
            if csv_writer:
                csv_writer.writerow([
                    i+1,
                    start_times[i],
                    start_duties[i],
                    ramp_times[i],
                    end_duties[i],
                    end_times[i],
                    rel_points,
                    rel_freq,
                    rel_power
                ])
            if not routine_running:
                controller.send_duty(0)
                break
            controller.send_duty(start_duties[i])
            dpg.set_value("test_progress", (i + 0.5) / steps)
            t0 = time.time()
            while routine_running and (time.time() - t0) < max(0, start_times[i]):
                time.sleep(0.01)
            if not routine_running:
                controller.send_duty(0)
                break
            controller.send_duty(end_duties[i])
            dpg.set_value("test_progress", (i + 1.0) / steps)
            t0 = time.time()
            while routine_running and (time.time() - t0) < max(0, end_times[i]):
                time.sleep(0.01)
            if not routine_running:
                controller.send_duty(0)
                break
            # --- Soft release after each step ---
            if soft_release_enabled:
                controller.send_soft_release(
                    end_duties[i],
                    rel_points,
                    rel_freq,
                    rel_power
                )
                if rel_freq > 0:
                    time.sleep(rel_points / rel_freq)
            else:
                controller.send_duty(0)
            time.sleep(post_roll)
        controller.send_duty(0)
    else:
        # --- Hardware trajectory routine with per-step recording ---
        for i in range(steps):
            velocity = round(end_duties[i], 2)
            take = str(i+1)
            filename = template.format(date=date_str, time=time_str, note=note, velocity=velocity, take=take)
            filepath = os.path.join(folder, filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            # Calculate release duration if needed
            if soft_release_enabled:
                rel_points = int(round(release_points_steps[i]))
                rel_freq = int(round(release_freq_steps[i]))
                rel_power = int(round(power_index_steps[i]))
                release_duration = rel_points / rel_freq if rel_freq > 0 else 0
            else:
                rel_points = 1
                rel_freq = 0
                rel_power = 0
                release_duration = 0
            duration = pre_roll + ramp_times[i]/1000.0 + start_times[i] + end_times[i]
            if include_release:
                duration += release_duration
            duration += post_roll
            audio_thread = threading.Thread(
                target=record_audio,
                args=(filepath, duration, sample_rate, channels, device, bit_depth),
                daemon=True
            )
            audio_thread.start()
            time.sleep(pre_roll)
            if not routine_running:
                break
            controller.queue_traj_segment(start_duties[i], end_duties[i], ramp_times[i], shape=1)
            dpg.set_value("test_progress", (i + 1.0) / steps)
            if csv_writer:
                csv_writer.writerow([
                    i+1,
                    start_times[i],
                    start_duties[i],
                    ramp_times[i],
                    end_duties[i],
                    end_times[i],
                    rel_points,
                    rel_freq,
                    rel_power
                ])
            # --- Soft release after each step ---
            if soft_release_enabled:
                controller.send_soft_release(
                    end_duties[i],
                    rel_points,
                    rel_freq,
                    rel_power
                )
                if rel_freq > 0:
                    time.sleep(rel_points / rel_freq)
            time.sleep(post_roll)
        controller.start_automation()
    if csv_file:
        csv_file.close()
    dpg.set_value("test_progress", 0)
    routine_running = False

def on_start_test(controller):
    if is_controller_ready(controller):
        if dpg.get_value("record_test_checkbox"):
            t = threading.Thread(target=run_test_routine_recorded, args=(controller,), daemon=True)
        else:
            t = threading.Thread(target=run_test_routine, args=(controller,), daemon=True)
        t.start()
    else:
        show_no_device_popup()

def update_button_states():
    if not device_connected:
        dpg.configure_item("stop_test", enabled=False)
        dpg.bind_item_theme("stop_test", "disabled_theme")
    elif pwm_active:
        dpg.configure_item("stop_test", enabled=True)
        dpg.bind_item_theme("stop_test", "active_theme")
    else:
        dpg.configure_item("stop_test", enabled=True)
        dpg.bind_item_theme("stop_test", "idle_theme")

    if pwm_active:
        dpg.bind_item_theme("start_test", "start_theme_active")
    else:
        dpg.bind_item_theme("start_test", "start_theme_idle")


def create_test_panel(controller):
    # Themes
    if not dpg.does_item_exist("active_theme"):
        with dpg.theme(tag="active_theme"):
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (200, 30, 30), category=dpg.mvThemeCat_Core)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 60, 60), category=dpg.mvThemeCat_Core)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (200, 0, 0), category=dpg.mvThemeCat_Core)

    if not dpg.does_item_exist("idle_theme"):
        with dpg.theme(tag="idle_theme"):
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (180, 60, 60), category=dpg.mvThemeCat_Core)

    if not dpg.does_item_exist("disabled_theme"):
        with dpg.theme(tag="disabled_theme"):
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (80, 80, 80), category=dpg.mvThemeCat_Core)

    if not dpg.does_item_exist("start_theme_active"):
        with dpg.theme(tag="start_theme_active"):
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (10, 180, 90), category=dpg.mvThemeCat_Core)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (20, 170, 100), category=dpg.mvThemeCat_Core)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (0, 160, 80), category=dpg.mvThemeCat_Core)

    if not dpg.does_item_exist("start_theme_idle"):
        with dpg.theme(tag="start_theme_idle"):
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (100, 150, 100), category=dpg.mvThemeCat_Core)

    # Layout
    numFieldWidth = 140
    spacerWidth = 20
    with dpg.group(horizontal=False):
        dpg.add_separator()
        dpg.add_text("Test Panel", tag="test_panel_title")
        dpg.add_separator()
        with dpg.group(horizontal=True):
            dpg.add_button(label="STOP", height=40, width=120, tag="stop_test",
                        callback=lambda s, a: on_stop(s, a, controller))
            dpg.add_button(label="Start Test", height=40, width=120, tag="start_test",
                           callback=lambda: on_start_test(controller))
            dpg.add_progress_bar(default_value=0.0, width=-1, tag="test_progress",
                                 overlay="Progress")
        dpg.add_spacer(height=6)
        dpg.add_separator()
        dpg.add_separator()
        dpg.add_spacer(height=6)
        dpg.add_text("First Iteration")
        with dpg.group(horizontal=True):
            with dpg.group(horizontal=False):
                dpg.add_text("Start Duty (%):")
                dpg.add_input_float(tag="start_duty_value_A", default_value=0.0, width=numFieldWidth, step=1.0,
                                    min_value=0.0, max_value=100.0, callback=None)
            dpg.add_spacer(width=spacerWidth)
            with dpg.group(horizontal=False):
                dpg.add_text("Holding Time (s):")
                dpg.add_input_float(tag="start_duty_time_A", default_value=2.0, width=numFieldWidth, step=1.0,
                                    callback=None)
            dpg.add_spacer(width=spacerWidth)
            with dpg.group(horizontal=False):
                dpg.add_text("Ramp (ms):")
                dpg.add_input_float(tag="ramp_time_ms_A", default_value=0.0, width=numFieldWidth, step=1.0,
                                    enabled=False, callback=None)
            dpg.add_spacer(width=spacerWidth)
            with dpg.group(horizontal=False):
                dpg.add_text("End Duty (%):")
                dpg.add_input_float(tag="end_duty_value_A", default_value=0.0, width=numFieldWidth, step=1.0,
                                    min_value=0.0, max_value=100.0, callback=None)
            dpg.add_spacer(width=spacerWidth)
            with dpg.group(horizontal=False):
                dpg.add_text("Holding Time (s):")
                dpg.add_input_float(tag="end_duty_time_A", default_value=2.0, width=numFieldWidth, step=1.0,
                                    callback=None)
        dpg.add_spacer(height=6)
        dpg.add_separator()
        dpg.add_spacer(height=6)
        dpg.add_text("Last Iteration")
        with dpg.group(horizontal=True):
            with dpg.group(horizontal=False):
                dpg.add_text("Start Duty (%):")
                dpg.add_input_float(tag="start_duty_value_B", default_value=0.0, width=numFieldWidth, step=1.0,
                                    min_value=0.0, max_value=100.0, callback=None)
            dpg.add_spacer(width=spacerWidth)
            with dpg.group(horizontal=False):
                dpg.add_text("Holding Time (s):")
                dpg.add_input_float(tag="start_duty_time_B", default_value=2.0, width=numFieldWidth, step=1.0,
                                    callback=None)
            dpg.add_spacer(width=spacerWidth)
            with dpg.group(horizontal=False):
                dpg.add_text("Ramp (ms):")
                dpg.add_input_float(tag="ramp_time_ms_B", default_value=0.0, width=numFieldWidth, step=1.0,
                                    enabled=False, callback=None)
            dpg.add_spacer(width=spacerWidth)
            with dpg.group(horizontal=False):
                dpg.add_text("End Duty (%):")
                dpg.add_input_float(tag="end_duty_value_B", default_value=0.0, width=numFieldWidth, step=1.0,
                                    min_value=0.0, max_value=100.0, callback=None)
            dpg.add_spacer(width=spacerWidth)
            with dpg.group(horizontal=False):
                dpg.add_text("Holding Time (s):")
                dpg.add_input_float(tag="end_duty_time_B", default_value=2.0, width=numFieldWidth, step=1.0,
                                    callback=None)
        dpg.add_spacer(height=6)
        dpg.add_separator()
        dpg.add_spacer(height=6)
        with dpg.group(horizontal=True):
            with dpg.group(horizontal=False):
                dpg.add_text("Steps:")
                dpg.add_input_int(tag="iterations", default_value=1, width=numFieldWidth, step=1.0, min_value=1, max_value=10000, min_clamped=True, max_clamped=True, callback=None)
            dpg.add_spacer(width=spacerWidth)
            with dpg.group(horizontal=False):
                dpg.add_text("Interpolation (Hz):")
                dpg.add_input_int(tag="rate", default_value=10000, width=numFieldWidth, step=1.0,
                                    callback=None)
        dpg.add_separator()
        dpg.add_spacer(height=20)
        with dpg.group(horizontal=True):
            with dpg.group(horizontal=False):        
                with dpg.group(horizontal=True):
                    dpg.add_checkbox(label="Soft Release", tag="soft_release_checkbox", default_value=False, callback=on_soft_release_changed)
                    dpg.add_text("", tag="soft_release_duration_label")
                with dpg.group(tag="soft_release_options_group", show=False):
                    dpg.add_input_int(label="Release Points", tag="soft_release_points_field", default_value=100, min_value=1, max_value=10000, min_clamped=True, max_clamped=True, width=120, callback=on_soft_release_param_changed)
                    dpg.add_input_int(label="Switching Frequency (Hz)", tag="soft_release_freq_field", default_value=200, min_value=1, max_value=10000, min_clamped=True, max_clamped=True, width=120, callback=on_soft_release_param_changed)
                    dpg.add_input_int(label="Power Index", tag="soft_release_power_field", default_value=1, min_value=1, max_value=9, min_clamped=True, max_clamped=True, width=120, callback=on_soft_release_param_changed)
            with dpg.group(horizontal=False):
                with dpg.group(horizontal = True, tag="release_iterations_checkbox", show = False):
                    dpg.add_checkbox(label="Test Release Parameters", tag="test_release_parameters_checkbox", default_value=False, callback=on_soft_release_test_changed)
                    dpg.add_text("", tag="soft_release_duration_label_last")
                with dpg.group(tag="release_iterations_group", show = False):
                    dpg.add_input_int(label="Release Points (final)", tag="soft_release_points_field_last", default_value=100, min_value=1, max_value=10000, min_clamped=True, max_clamped=True, width=120, callback=on_soft_release_final_param_changed)
                    dpg.add_input_int(label="Switching Frequency (Hz, final)", tag="soft_release_freq_field_last", default_value=200, min_value=1, max_value=10000, min_clamped=True, max_clamped=True, width=120, callback=on_soft_release_final_param_changed)
                    dpg.add_input_int(label="Power Index (final)", tag="soft_release_power_field_last", default_value=1, min_value=1, max_value=9, min_clamped=True, max_clamped=True, width=120, callback=on_soft_release_final_param_changed)
        dpg.add_separator()
        dpg.add_spacer(height=20)
        dpg.add_checkbox(label="Record Test", tag="record_test_checkbox", default_value=False, callback=on_record_test_changed)
        with dpg.group(tag="recording_options_group", show=False):
            dpg.add_input_int(label="Pre-roll (ms)", tag="pre_roll_field", default_value=0, min_value=0, max_value=10000, width=120)
            with dpg.group(horizontal=True):
                dpg.add_input_int(label="Post-roll (ms)", tag="post_roll_field", default_value=0, min_value=0, max_value=10000, width=120)
                dpg.add_checkbox(label="Include Release in Recording", tag="include_release_in_recording_checkbox", default_value=False)
            dpg.add_input_text(label="Key", tag="note_field", default_value="default", width=120)
            dpg.add_checkbox(label="Export CSV", tag="export_csv_checkbox", default_value=True)

    # Store controller for update_button_states
    update_button_states()
