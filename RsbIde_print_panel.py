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
def print_to_panel(view, text, b_overwrite=True, bLog=False):
    global b_helper_panel_on, output_view
    text.replace("\r", "")
    b_helper_panel_on = True
    if not ST3:
        if b_overwrite or not output_view:
            # get_output_panel doesn't "get" the panel, it *creates* it, so we should only call get_output_panel once
            panel = view.window().get_output_panel('Rsb_panel')
            output_view = panel
        else:
            panel = output_view
        panel_edit = panel.begin_edit()
        panel.insert(panel_edit, panel.size(), text)
        panel.end_edit(panel_edit)
    else:
        if b_overwrite or not output_view:
            panel = view.window().create_output_panel('Rsb_panel')
            output_view = panel
        else:
            panel = output_view
        # panel.run_command('erase_view')
        # print(text)
        panel.run_command('append', {'characters': text})

    if not b_overwrite:
        panel.show(panel.size())

    if bLog:
        panel.set_syntax_file("Packages/UnrealScriptIDE/Log.tmLanguage")
        panel.set_name("UnrealLog")
    else:
        panel.set_syntax_file(view.settings().get('syntax'))

    view.window().run_command("show_panel", {"panel": "output.Rsb_panel"})

