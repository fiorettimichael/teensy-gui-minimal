import dearpygui.dearpygui as dpg

def load_custom_font():
    with dpg.font_registry():
        default_font = dpg.add_font("assets/OpenSans-Regular.ttf", 18)
        logger_font = dpg.add_font("assets/SourceCodePro-Regular.otf", 14)
        dpg.bind_font(default_font)

def apply_global_theme():
    with dpg.theme() as global_theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (39, 39, 41), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_Button, (50, 85, 127), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (45, 65, 97), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (65, 95, 127), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_Border, (10, 10, 8), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (23, 23, 24), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (38, 43, 52), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, (38, 43, 52), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_Text, (230, 230, 230), category=dpg.mvThemeCat_Core)
            #dpg.add_theme_color(dpg.mvThemeCol_TabActive, (40, 70, 100), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, (40, 70, 100), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, (40, 70, 100), category=dpg.mvThemeCat_Core)

            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding,3)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 7)
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 9)
            dpg.add_theme_style(dpg.mvStyleVar_GrabRounding, 3)

            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 10, 8)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 7, 7)

            dpg.add_theme_color(dpg.mvThemeCol_PlotLines, (185, 170, 90), category=dpg.mvThemeCat_Core)

    dpg.bind_theme(global_theme)

    # Gray / disabled
    with dpg.theme(tag="status_theme_disconnected"):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (100,100,100))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (120,120,120))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (80,80,80))

    # Orange / connecting
    with dpg.theme(tag="status_theme_connecting"):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (200,150,50))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (220,170,70))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (180,130,30))

    # Green / connected
    with dpg.theme(tag="status_theme_connected"):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (50,200,100))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (70,220,120))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (30,180,80))


