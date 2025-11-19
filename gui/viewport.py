import dearpygui.dearpygui as dpg
import os
from config import menu_items
from gui.themes import (load_custom_font, apply_global_theme)
from gui.device_panel import create_serial_port_panel
from gui.control_panel import create_control_panel
from gui.logger import log
from gui.test_panel import create_test_panel
from gui.sound_panel import create_sound_panel

def toggle_panel_visibility(sender, app_data, tag):
    dpg.configure_item(tag, show=app_data)

def handle_window_closed(sender, app_data, user_data):
    dpg.set_value(menu_items[user_data], False)

def make_toggle_callback(tag):
    return lambda sender, app_data: toggle_panel_visibility(sender, app_data, tag)

def sync_menu_with_panel_visibility():
    for tag, menu_item_tag in menu_items.items():
        is_visible = dpg.is_item_shown(tag)
        dpg.set_value(menu_item_tag, is_visible)

def setup_gui(controller):
    dpg.create_context()
    dpg.configure_app(docking=True, docking_space=True)

    if os.path.exists("layout.ini"):
        dpg.configure_app(init_file="layout.ini", load_init_file=True)

    dpg.create_viewport(title="Teensy Solenoid Control", width=800, height=600)

    dpg.setup_dearpygui()

    with dpg.window(tag="MainWindow", label="Main Window"):
        with dpg.viewport_menu_bar():
            with dpg.menu(label="Viewport"):
                for label, tag in [
                    ("Serial Port", "serial_panel"),
                    ("Control Panel", "control_panel"),
                    ("Log Output", "log_panel"),
                    ("Debug Panel", "debug_panel"),
                    ("Packet Monitor", "packet_monitor"),
                    ("Test Panel", "test_panel"),
                    ("Sound Panel", "sound_panel"),
                ]:
                    menu_item_id = dpg.generate_uuid()
                    dpg.add_menu_item(
                        label=label,
                        check=True,
                        default_value=True,
                        callback=make_toggle_callback(tag),
                        tag=menu_item_id
                    )
                    menu_items[tag] = menu_item_id

            with dpg.menu(label="Layout"):
                dpg.add_menu_item(label="Save Layout", callback=lambda: dpg.save_init_file("layout.ini"))

    # Dockable panels
    with dpg.window(label="Controller", tag="serial_panel", width=300, height=100, pos=(10, 50), on_close=handle_window_closed, user_data="serial_panel"):
        create_serial_port_panel(controller)
    with dpg.window(label="Control Panel", tag="control_panel", width=300, height=200, pos=(10, 160), on_close=handle_window_closed, user_data="control_panel"):
        create_control_panel(controller)
    with dpg.window(label="Log Output", tag="log_panel", width=720, height=120, pos=(10, 370), on_close=handle_window_closed, user_data="log_panel"):
        log.create_log_panel()
    with dpg.window(label="Debug Panel", tag="debug_panel", width=720, height=120, pos=(10, 370), on_close=handle_window_closed, user_data="log_panel"):
        log.create_debug_panel()
    with dpg.window(label="Packet Monitor", tag="packet_monitor", width=720, height=120, pos=(10, 370), on_close=handle_window_closed, user_data="log_panel"):
        log.create_packet_monitor()
    with dpg.window(label="Test Panel", tag="test_panel", width=600, height=300, pos=(350, 200), on_close=handle_window_closed, user_data="test_panel"):
        create_test_panel(controller)
    with dpg.window(label="Sound Device", tag="sound_panel", width=600, height=300, pos=(350, 200), on_close=handle_window_closed, user_data="sound_panel"):
        create_sound_panel()

    dpg.set_primary_window("MainWindow", True)
    
    load_custom_font()
    apply_global_theme()

    dpg.show_viewport()
    dpg.maximize_viewport()

    dpg.start_dearpygui()
