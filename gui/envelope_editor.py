import time
import dearpygui.dearpygui as dpg
from config import envelope_points  # [(0.0, 0.5), (1.0, 0.5)]

plot_tag = "envelope_plot"
series_tag = "envelope_series"

def on_send_envelope():
    # Placeholder for sending the envelope to the device
    print("Sending envelope to device...")
    time.sleep(1)  # Simulate delay
    print("Envelope sent!")

def redraw_envelope():
    x_vals = [pt[0] for pt in envelope_points]
    y_vals = [pt[1] for pt in envelope_points]

    dpg.delete_item("series_data")  # fully delete old line
    dpg.add_line_series(x_vals, y_vals, tag="series_data", parent="y_axis")

    dpg.bind_item_theme("series_data", "plot_theme")

def make_point_drag_callback():
    def callback(sender, app_data, user_data):
        index, envelope_points = user_data

        # Always retrieve current position manually
        current_x, current_y = dpg.get_value(sender)

        # Clamp x for the first and last points
        if index == 0:
            current_x = 0.0
        elif index == len(envelope_points) - 1:
            current_x = 1.0
        else:
            left_x = envelope_points[index - 1][0]
            right_x = envelope_points[index + 1][0]
            # Must stay between neighbors
            current_x = max(left_x + 0.001, min(right_x - 0.001, current_x))
        # Optional: clamp y between 0 and 1
        current_y = max(0.0, min(1.0, current_y))

        # Update the data
        envelope_points[index] = (current_x, current_y)

        # Force the drag point to stay within constraints
        dpg.set_value(sender, [current_x, current_y])

        # Redraw the connecting line
        redraw_envelope()
    return callback



def add_drag_points():
    for i, (x, y) in enumerate(envelope_points):
        dpg.add_drag_point(
            parent=plot_tag,
            tag=f"drag_point_{i}",
            default_value=[x, y],
            label=f"P{i}",
            color=(255, 0, 0),
            show_label=True,
            delayed=True,
            user_data=(i, envelope_points),
            callback=make_point_drag_callback()
        )

def add_node_at_mouse():
    mouse_x, mouse_y = dpg.get_plot_mouse_pos()

    # Clamp to [0, 1] just in case
    mouse_x = max(0.0, min(1.0, mouse_x))
    mouse_y = max(0.0, min(1.0, mouse_y))

    insert_node((mouse_x, mouse_y))

    dpg.hide_item("custom_popup_window")

def insert_node(new_point):
    envelope_points.append(new_point)

    # Sort points by x value
    envelope_points.sort(key=lambda pt: pt[0])

    # Rebuild all drag points
    rebuild_drag_points()
    redraw_envelope()

def rebuild_drag_points():
    # First remove all previous drag points
    for i in range(len(envelope_points) + 5):  # +5 margin just in case
        if dpg.does_item_exist(f"drag_point_{i}"):
            dpg.delete_item(f"drag_point_{i}")

    # Re-add fresh ones
    add_drag_points()

def insert_node_from_popup():
    x = dpg.get_value("input_x")
    y = dpg.get_value("input_y")

    # Clamp to 0-1 range
    x = max(0.0, min(1.0, x))
    y = max(0.0, min(1.0, y))

    point = (x, y)

    insert_node(point)

    # Cleanup
    if dpg.does_item_exist("type_coords_popup"):
        dpg.delete_item("type_coords_popup")


def open_type_coordinates_popup():
    with dpg.window(
        label="Insert Node by Coordinates",
        modal=True,
        popup=True,           
        no_title_bar=False,
        tag="type_coords_popup",
        width=300,
        height=220,
        pos=(300, 300),
        on_close=lambda: dpg.delete_item("type_coords_popup")  # Close the popup when the window is closed
    ):
        dpg.add_text("Enter Coordinates (Normalized 0-1):")
        dpg.add_input_float(label="X", tag="input_x", default_value=0.5, min_value=0.0, max_value=1.0, step=0.01)
        dpg.add_input_float(label="Y", tag="input_y", default_value=0.5, min_value=0.0, max_value=1.0, step=0.01)
        dpg.add_separator()
        with dpg.group(horizontal=True):
            dpg.add_button(label="Insert Node", callback=insert_node_from_popup)
            dpg.add_button(label="Cancel", callback=lambda: dpg.delete_item("type_coords_popup"))
        
        dpg.hide_item("custom_popup_window")

def mouse_click_callback(sender, app_data):
    if (dpg.is_key_down(dpg.mvKey_LAlt) or dpg.is_key_down(dpg.mvKey_RAlt))  and (app_data == dpg.mvMouseButton_Right or app_data == dpg.mvMouseButton_Left):
        if dpg.is_item_hovered(plot_tag):
            mouse_pos = dpg.get_mouse_pos(local=False)
            dpg.configure_item("custom_popup_window", pos=mouse_pos)
            dpg.show_item("custom_popup_window")
    else:
        if dpg.is_item_shown("custom_popup_window") and not dpg.is_item_hovered("custom_popup_window") and not dpg.is_item_hovered("pop_up_group"):
            dpg.hide_item("custom_popup_window")

def create_envelope_editor_panel():
    global line_theme

    with dpg.group():
        dpg.add_text("Envelope Editor")
        dpg.add_separator()

        with dpg.theme(tag="plot_theme"):
            with dpg.theme_component(dpg.mvLineSeries):
                dpg.add_theme_color(dpg.mvPlotCol_Line, (150, 255, 60), category=dpg.mvThemeCat_Plots)

        with dpg.plot(tag=plot_tag, height=300, width=-1, zoom_rate=0.05, no_menus=False):
            dpg.add_plot_axis(dpg.mvXAxis, tag="x_axis")
            with dpg.plot_axis(dpg.mvYAxis, tag="y_axis"):
                dpg.add_line_series([], [], tag="series_data", parent="y_axis")

                with dpg.handler_registry():
                    dpg.add_mouse_click_handler(callback=mouse_click_callback)
            dpg.bind_item_theme("series_data", "plot_theme")

            dpg.set_axis_zoom_constraints("x_axis", 0.0, 1.0)
            dpg.set_axis_zoom_constraints("y_axis", 0.0, 1.0)
            dpg.set_axis_limits_constraints("x_axis", 0.0, 1.0)
            dpg.set_axis_limits_constraints("y_axis", 0.0, 1.0)

                 

        # Create a hidden window that acts as the popup
        with dpg.window(label="Add Node",
            tag="custom_popup_window",
            no_title_bar=False,
            no_move=True,
            no_resize=True,
            no_collapse=True,
            no_background=False,
            show=False,
            autosize=True
            ):
            with dpg.group(tag = "pop_up_group"):
                dpg.add_button(label="Insert Here", callback=add_node_at_mouse)
                dpg.add_button(label="Type Coordinates)", callback=open_type_coordinates_popup)



    redraw_envelope()
    add_drag_points()


