import dearpygui.dearpygui as dpg
import serial.tools.list_ports
from config import serial_port

# Global tags
PORT_COMBO_TAG = "serial_port_combo"
PORT_PANEL_CONTENT_TAG = "serial_panel_content"
STATUS_GROUP_TAG = "status_display_group"
REFRESH_BUTTON_TAG = "serial_refresh_button"
STATUS_LABEL = "Unconnected"
STATUS_BUTTON_TAG = "serial_status_button"
FREQ_CONTROL_TAG = "pwm_freq_field"

def get_available_ports():
    return [port.device for port in serial.tools.list_ports.comports()]

def refresh_ports():
    ports = get_available_ports()
    dpg.configure_item(PORT_COMBO_TAG, items=ports)
    if ports:
        dpg.set_value(PORT_COMBO_TAG, ports[0])

def on_refresh_pressed():
    refresh_ports()

def _confirm_disconnect(controller):
    dpg.delete_item("confirm_disconnect")
    controller.close()

def on_status_pressed(controller):
    if not dpg.does_item_exist("confirm_disconnect"):
        with dpg.window(modal=True, tag="confirm_disconnect", no_title_bar=False,
                        width=300, height=120):
            dpg.add_text("Disconnect from device?")
            with dpg.group(horizontal=True):
                dpg.add_button(label="Yes", callback=lambda s,a,u: _confirm_disconnect(u),
                            user_data=controller)
                dpg.add_button(label="No", callback=lambda: dpg.delete_item("confirm_disconnect"))
        
def on_port_selected(sender, app_data, user_data):
    controller = user_data
    port = app_data
    try:
        controller.connect(port)
        print(f"Connected to {port}")
        populate_menu(controller)
    except Exception as e:
        print(f"Failed to connect: {e}")

def populate_menu(controller):
    if dpg.does_item_exist(STATUS_GROUP_TAG):
        dpg.delete_item(STATUS_GROUP_TAG, children_only=False)

    try:
        status = controller.get_status()
    except Exception as e:
        print(f"Failed to fetch status: {e}")
        return

    try:
        (freq_key, freq_value) = list(status.items())[4]
        dpg.set_value(FREQ_CONTROL_TAG, freq_value)
    except Exception as e:
        print(f"Failed to reach GUI item: {e}")
        return

    
    with dpg.child_window(parent=PORT_PANEL_CONTENT_TAG, tag=STATUS_GROUP_TAG, label="Device Settings"):

        dpg.add_separator()
        with dpg.group(horizontal=True):
            (key, value) = list(status.items())[0]
            dpg.add_text(key.replace("_", " ").capitalize() + "\t" + str(value))
        dpg.add_separator()
        dpg.add_spacer(height=4)

        with dpg.group(tag = "pwm_out_settings"):

            (pin_key, pin_value) = list(status.items())[1]
            (freq_key, freq_value) = list(status.items())[4]
            (depth_key, depth_value) = list(status.items())[9]
            with dpg.group(horizontal=True):
                dpg.add_text("PWM Output Pin")
                with dpg.group(horizontal=True):
                    dpg.add_input_int(
                            default_value=pin_value,
                            step=0,
                            readonly=True,
                            min_clamped=True,
                            width=50,
                            callback= None,
                            tag=f"status_{pin_key}"
                        )
            dpg.add_separator()
            with dpg.group(horizontal=True):
                with dpg.group():
                    dpg.add_text("Frequency")
                    dpg.add_text("Depth")
                with dpg.group():
                    dpg.add_input_int(
                        default_value=freq_value,
                        step=0,
                        readonly=False,
                        min_clamped=True,
                        width=150,
                        callback=on_pwm_freq_changed,
                        user_data=controller,
                        tag=f"status_{freq_key}")
                    dpg.add_input_int(
                        default_value=depth_value,
                        step=0,
                        readonly=True,
                        min_clamped=True,
                        width=150,
                        callback=None,
                        user_data=controller,
                        tag=f"status_{depth_key}")
                with dpg.group():
                    dpg.add_text("Hz")
                    dpg.add_text("bit")
            dpg.add_spacer(height=4)
        
        with dpg.group(tag = "pwm_adc_settings"):
            (pin_key, pin_value) = list(status.items())[2]
            (rate_key, rate_value) = list(status.items())[5]
            (res_key, res_value) = list(status.items())[7]
            with dpg.group(horizontal=True):
                dpg.add_text("PWM Monitor Pin")
                with dpg.group(horizontal=True):
                    dpg.add_input_int(
                            default_value=pin_value,
                            step=0,
                            readonly=True,
                            min_clamped=True,
                            width=50,
                            callback= None,
                            tag=f"status_{pin_key}"
                        )
            dpg.add_separator()
            with dpg.group(horizontal=True):
                with dpg.group():
                    dpg.add_text("Rate")
                    dpg.add_text("Resolution")
                with dpg.group():
                    dpg.add_input_int(
                        default_value=rate_value,
                        step=0,
                        readonly=False,
                        min_clamped=True,
                        width=150,
                        callback=on_pwm_freq_changed,
                        user_data=controller,
                        tag=f"status_{rate_key}")
                    dpg.add_input_int(
                        default_value=res_value,
                        step=0,
                        readonly=True,
                        min_clamped=True,
                        width=150,
                        callback=None,
                        user_data=controller,
                        tag=f"status_{res_key}")
                with dpg.group():
                    dpg.add_text("Hz")
                    dpg.add_text("bit")
            dpg.add_spacer(height=4)

        with dpg.group(tag = "primary_adc_settings"):
            (pin_key, pin_value) = list(status.items())[3]
            (rate_key, rate_value) = list(status.items())[6]
            (res_key, res_value) = list(status.items())[8]
            with dpg.group(horizontal=True):
                dpg.add_text("Primary ADC Pin")
                with dpg.group(horizontal=True):
                    dpg.add_input_int(
                            default_value=pin_value,
                            step=0,
                            readonly=True,
                            min_clamped=True,
                            width=50,
                            callback= None,
                            tag=f"status_{pin_key}"
                        )
            dpg.add_separator()
            with dpg.group(horizontal=True):
                with dpg.group():
                    dpg.add_text("Rate")
                    dpg.add_text("Resolution")
                with dpg.group():
                    dpg.add_input_int(
                        default_value=rate_value,
                        step=0,
                        readonly=True,
                        min_clamped=True,
                        width=150,
                        callback=on_pwm_freq_changed,
                        user_data=controller,
                        tag=f"status_{rate_key}")
                    dpg.add_input_int(
                        default_value=res_value,
                        step=0,
                        readonly=True,
                        min_clamped=True,
                        width=150,
                        callback=None,
                        user_data=controller,
                        tag=f"status_{res_key}")
                with dpg.group():
                    dpg.add_text("Hz")
                    dpg.add_text("bit")
            dpg.add_spacer(height=4)

"""     
        with dpg.group(horizontal=True):
            with dpg.group(width=180):
                for key, value in status.items():
                    dpg.add_text(key.replace("_", " ").capitalize())
            with dpg.group(width=70):
                for key, value in status.items():    
                    read_only = key != "pwm_frequency"
                    if key == "firmware_version":
                        dpg.add_separator()
                        dpg.add_input_text(multiline=False, readonly=True, tag = "version")
                        dpg.set_value("version", value)
                        dpg.add_separator()
                        dpg.add_spacer(height=5)
                    else:
                        dpg.add_input_int(
                            default_value=value,
                            step=0,
                            readonly=read_only,
                            min_clamped=True,
                            width=150,
                            callback=on_pwm_freq_changed if key == "pwm_frequency" else None,
                            tag=f"status_{key}"
                        )
"""
def on_pwm_freq_changed(sender, app_data, user_data=None):
    new_freq = app_data
    print(f"[GUI] PWM frequency changed to: {new_freq}")
    # TODO: Send real-time update to Teensy using controller

def create_serial_port_panel(controller):
    with dpg.group(tag=PORT_PANEL_CONTENT_TAG):
        dpg.add_text("Serial Port")
        dpg.add_separator()
        with dpg.group(horizontal=True):
            ports = get_available_ports()
            dpg.add_combo(
                items=ports,
                default_value=ports[0] if ports else "",
                callback=on_port_selected,
                user_data=controller,
                tag=PORT_COMBO_TAG,
                width=220
            )
            dpg.add_button(label="Rescan", callback=on_refresh_pressed, tag=REFRESH_BUTTON_TAG)
        dpg.add_spacer(height=10)
        with dpg.group(horizontal=True):        
            dpg.add_text("Device Status")
            dpg.add_button(label="Unconnected",
                           tag=STATUS_BUTTON_TAG,
                           callback=None)
            dpg.bind_item_theme(STATUS_BUTTON_TAG, "status_theme_disconnected")
        dpg.add_separator()