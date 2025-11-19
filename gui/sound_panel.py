import dearpygui.dearpygui as dpg
import sounddevice as sd
import os

# Global tags
SOUND_DEVICE_COMBO_TAG = "sound_device_combo"
SOUND_PANEL_CONTENT_TAG = "sound_panel_content"
SOUND_REFRESH_BUTTON_TAG = "sound_refresh_button"
SOUND_INFO_BUTTON_TAG = "sound_info_button"
SOUND_INFO_POPUP_TAG = "sound_info_popup"
SOUND_SELECTED_LABEL_TAG = "sound_selected_label"

def get_input_devices():
    devices = sd.query_devices()
    return [d['name'] for d in devices if d['max_input_channels'] > 0]

def refresh_sound_devices():
    devices = get_input_devices()
    dpg.configure_item(SOUND_DEVICE_COMBO_TAG, items=devices)
#''''
#    if devices:
#       dpg.set_value(SOUND_DEVICE_COMBO_TAG, devices[0])
#       dpg.set_value(SOUND_SELECTED_LABEL_TAG, f"Selected: {devices[0]}")
#   else:
#       dpg.set_value(SOUND_SELECTED_LABEL_TAG, "Selected: None")
#''''

def on_refresh_sound_pressed():
    refresh_sound_devices()

def on_sound_device_selected(sender, app_data, user_data):
    dpg.set_value(SOUND_SELECTED_LABEL_TAG, f"Selected: {app_data}")

def on_sound_info_pressed():
    selected = dpg.get_value(SOUND_DEVICE_COMBO_TAG)
    info = None
    for d in sd.query_devices():
        if d['name'] == selected:
            info = d
            break
    if info:
        if dpg.does_item_exist(SOUND_INFO_POPUP_TAG):
            dpg.delete_item(SOUND_INFO_POPUP_TAG)
        with dpg.window(modal=True, tag=SOUND_INFO_POPUP_TAG, no_title_bar=False, width=350, height=180):
            dpg.add_text(f"Device: {info['name']}")
            dpg.add_text(f"Channels: {info['max_input_channels']}")
            dpg.add_text(f"Default samplerate: {info['default_samplerate']}")
            dpg.add_text(f"Latency: {info['default_low_input_latency']:.3f} - {info['default_high_input_latency']:.3f} s")
            dpg.add_button(label="OK", width=100, callback=lambda: dpg.delete_item(SOUND_INFO_POPUP_TAG))

def create_sound_panel():
    with dpg.group(tag=SOUND_PANEL_CONTENT_TAG):
        # Device selection
        dpg.add_text("Input Sound Device")
        dpg.add_separator()
        with dpg.group(horizontal=True):
            devices = get_input_devices()
            dpg.add_combo(
                items=devices,
                default_value=devices[0] if devices else "",
                callback=on_sound_device_selected,
                tag=SOUND_DEVICE_COMBO_TAG,
                width=220
            )
            dpg.add_button(label="Refresh", callback=on_refresh_sound_pressed, tag=SOUND_REFRESH_BUTTON_TAG)
            dpg.add_button(label="Device Info", callback=on_sound_info_pressed, tag=SOUND_INFO_BUTTON_TAG)
        dpg.add_text("Selected: None", tag=SOUND_SELECTED_LABEL_TAG)
        dpg.add_separator()
        dpg.add_spacer(height=10)

        # Recording parameters
        dpg.add_text("Recording")
        dpg.add_separator()
        with dpg.group(horizontal=False):
            with dpg.group(horizontal=True):
                dpg.add_text("Sample Rate (kHz)")
                dpg.add_combo(items=["24", "44.1", "48", "96"], tag="sample_rate_field", default_value="48", width=100)
            dpg.add_spacer(height=4)
            with dpg.group(horizontal=True):
                dpg.add_text("Bit Depth")
                dpg.add_combo(items=["float64", "float32", "int32", "int16", "int8", "uint8"], default_value="float32", tag="bit_depth_combo", width=100)
            dpg.add_spacer(height=4)
            with dpg.group(horizontal=True):    
                dpg.add_text("Channels")
                dpg.add_input_int(tag="channel_count_field", default_value=1, min_value=1, max_value=32, width=120)
        dpg.add_spacer(height=6)
        dpg.add_separator()
        dpg.add_spacer(height=10)

        # Storage
        dpg.add_text("Storage")
        dpg.add_separator()
        with dpg.group(horizontal=True):
            dpg.add_text("Parent Folder")
            dpg.add_input_text(tag="parent_folder_field", default_value=os.path.expanduser("~/recordings"), width=220)
            # TODO filedialog
        dpg.add_text("Folder Structure")
        dpg.add_input_text(tag="folder_template_field", default_value="session_{date}/{time}/{note}/{velocity}_{take}.wav", width=320)
        #dpg.add_checkbox(label="Auto-organize per channel", tag="auto_organize_checkbox", default_value=True)
        dpg.add_spacer(height=6)
        dpg.add_separator()
