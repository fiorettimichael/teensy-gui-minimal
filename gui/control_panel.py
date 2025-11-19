import dearpygui.dearpygui as dpg
from config import pwm_depth

device_connected = True
pwm_active = False

def show_no_device_popup():
    if dpg.does_item_exist("no_device_popup"):
        if dpg.is_item_shown("no_device_popup"):
            return
        else:
            dpg.delete_item("no_device_popup")
    
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


def send_duty(controller, percent):
    try:
        controller.send_duty(percent)
    except Exception as e:
        print(f"[Error] Failed to send duty cycle: {e}")
        show_no_device_popup()

def send_pwm_frequency(controller, freq):
    freq = int(max(1000, min(100000, int(freq))))
    try:
        controller.set_pwm_frequency(freq)
    except Exception as e:
        print(f"[Error] Failed to send PWM frequency: {e}")
        show_no_device_popup()

def on_pwm_freq_enter(sender, app_data, user_data):
    controller = user_data
    try:
        freq = int(app_data)
    except Exception:
        freq = 0
    freq = max(1000, min(100000, freq))
    dpg.set_value(sender, freq)
    if is_controller_ready(controller):
        send_pwm_frequency(controller, freq)
    else:
        show_no_device_popup()

def update_pwm_freq_field(controller):
    if is_controller_ready(controller):
        try:
            freq = 0
            if hasattr(controller, "get_status"):
                status = controller.get_status()
                freq = int(status.get("pwm_frequency", 0))
            dpg.configure_item("pwm_freq_field", enabled=True, default_value=freq)
        except Exception:
            dpg.configure_item("pwm_freq_field", enabled=True, default_value=0)
    else:
        dpg.configure_item("pwm_freq_field", enabled=False, default_value=0)

def is_controller_ready(controller):
    return controller and hasattr(controller, 'ser') and controller.ser and controller.ser.is_open

def on_stop(sender, app_data, controller):
    global pwm_active
    if is_controller_ready(controller):
        controller.stop_pwm() 
        pwm_active = False
        update_button_states()
    else:
        show_no_device_popup()

def on_pwm(sender, app_data, controller):
    global pwm_active
    if is_controller_ready(controller):
        duty = dpg.get_value("duty_slider")
        send_duty(controller, duty)
        pwm_active = True
        update_button_states()
    else:
        show_no_device_popup()

def on_set_on(controller):
    if is_controller_ready(controller):
        send_duty(controller, 100.0)
    else:
        show_no_device_popup()

def on_slider_change(sender, app_data, user_data):
    controller = user_data
    if pwm_active and controller and is_controller_ready(controller):
        send_duty(controller, app_data)

def update_button_states():
    if not device_connected:
        dpg.configure_item("stop_button", enabled=False)
        dpg.bind_item_theme("stop_button", "disabled_theme")
    elif pwm_active:
        dpg.configure_item("stop_button", enabled=True)
        dpg.bind_item_theme("stop_button", "active_theme")
    else:
        dpg.configure_item("stop_button", enabled=True)
        dpg.bind_item_theme("stop_button", "idle_theme")

    if pwm_active:
        dpg.bind_item_theme("start_pwm_button", "start_theme_active")
    else:
        dpg.bind_item_theme("start_pwm_button", "start_theme_idle")


def create_control_panel(controller):
    # Themes
    with dpg.theme(tag="active_theme"):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (200, 30, 30), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 60, 60), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (200, 0, 0), category=dpg.mvThemeCat_Core)

    with dpg.theme(tag="idle_theme"):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (180, 60, 60), category=dpg.mvThemeCat_Core)

    with dpg.theme(tag="disabled_theme"):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (80, 80, 80), category=dpg.mvThemeCat_Core)

    with dpg.theme(tag="start_theme_active"):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (10, 180, 90), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (20, 170, 100), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (0, 160, 80), category=dpg.mvThemeCat_Core)

    with dpg.theme(tag="start_theme_idle"):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (100, 150, 100), category=dpg.mvThemeCat_Core)

    # Layout
    with dpg.group(horizontal=False):
        dpg.add_separator()
        dpg.add_spacer(height=6)
        dpg.add_button(label="STOP", height=60, width=-1, tag="stop_button",
                       callback=lambda s, a: on_stop(s, a, controller))
        dpg.add_spacer(height=6)
        dpg.add_separator()
        dpg.add_spacer(height=20)
        dpg.add_separator()
        dpg.add_spacer(height=6)
        dpg.add_button(label="PWM", height=50, width=-1, tag="start_pwm_button",
                       callback=lambda s, a: on_pwm(s, a, controller))
        dpg.add_text("Duty Cycle (%)")
        dpg.add_slider_float(tag="duty_slider", default_value=50.0, min_value=0.0, max_value=100.0, width=-1,
                             callback=on_slider_change, user_data=controller)

        dpg.add_text("PWM Frequency (Hz)")
        dpg.add_input_int(
            tag="pwm_freq_field",
            default_value=0,
            width=-1,
            min_value=1000,
            max_value=100000,
            step=100,
            on_enter=True,
            callback=on_pwm_freq_enter,
            user_data=controller
        )
        dpg.add_spacer(height=6)
        dpg.add_separator()
        dpg.add_spacer(height=20)
        dpg.add_button(label="Set ON", height=40, width=80, callback=lambda: on_set_on(controller))


    update_button_states()
