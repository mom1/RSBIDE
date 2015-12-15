# coding=cp1251
# -------------
import sublime

ST3 = int(sublime.version()) > 3000

if ST3:
    basestring = (str, bytes)

import re

# if the helper panel is displayed, this is true
# ! (TODO): use an event instead
b_helper_panel_on = False
output_view = None


# prints the text to the "helper panel" (Actually the console)
# ! (TODO): fire show_helper_panel
def print_to_panel(view, text, b_overwrite=True, bLog=False, bDoc=False, showline=1):
    global b_helper_panel_on, output_view
    b_helper_panel_on = True
    if b_overwrite or not output_view:
        panel = view.window().create_output_panel('Rsb_panel')
        output_view = panel
    else:
        panel = output_view
    panel.set_read_only(False)
    # panel.run_command('erase_view')
    # print(text)
    panel.run_command('append', {'characters': text})

    if not b_overwrite:
        panel.show(panel.size())

    if bLog:
        # panel.set_syntax_file("Packages/UnrealScriptIDE/Log.tmLanguage")
        pass
    elif bDoc:
        # panel.set_syntax_file('INI')
        pass
    else:
        panel.set_syntax_file(view.settings().get('syntax'))

    panel.show_at_center(panel.line(panel.text_point(showline-1, 0)-1))
    panel.set_read_only(True)
    panel.show(0)
    view.window().run_command("show_panel", {"panel": "output.Rsb_panel"})


def get_panel(view, text, b_overwrite=True, bLog=False):
    panel = view.window().create_output_panel('Rsb_parse_panel')
    panel.set_read_only(False)
    panel.run_command('append', {'characters': text})

    panel.set_syntax_file(view.settings().get('syntax'))

    panel.set_read_only(True)
    return panel
