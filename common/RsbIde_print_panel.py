# -*- coding: utf-8 -*-
# -------------
import sublime
from RSBIDE.common.async import run_after_loading
# from RSBIDE.common.notice import *

ST3 = int(sublime.version()) > 3000

if ST3:
    basestring = (str, bytes)

# if the helper panel is displayed, this is true
# ! (TODO): use an event instead
b_helper_panel_on = False
output_view = None


# prints the text to the "helper panel" (Actually the console)
def print_to_panel(view, text, b_overwrite=True, bLog=False, bDoc=False, showline=0, region_mark=None):
    global b_helper_panel_on, output_view
    b_helper_panel_on = True
    name_panel = ''

    if bLog:
        name_panel = 'RSBIDE:Log'
    elif bDoc:
        name_panel = 'RSBIDE:Documentation'
    else:
        name_panel = 'RSBIDE:Declaration'

    if b_overwrite or not output_view:
        kill_panel(name_panel)
        panel = view.window().create_output_panel(name_panel, False)
        output_view = panel
    else:
        panel = output_view
    panel.set_read_only(False)
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

    def show_at_center():
        panel.show_at_center(region)

    if showline > 0:
        position = panel.text_point(showline, 0)
        region = panel.line(position)
        run_after_loading(panel, show_at_center)

    if region_mark:
        rm = panel.word(panel.text_point(*region_mark))
        panel.add_regions('rsbide_declare', [rm], 'string', 'dot', sublime.DRAW_NO_FILL)
    elif showline > 0:
        panel.add_regions('rsbide_declare', [region], 'string', 'dot', sublime.DRAW_NO_FILL)

    panel.set_read_only(True)
    view.window().run_command("show_panel", {"panel": "output.%s" % name_panel})


def get_panel(view, text, name_panel='Rsb_parse_panel', syntax='Packages/RSBIDE/HighlightSyntax/R-Style.sublime-syntax'):
    kill_panel(name_panel)
    panel = view.window().create_output_panel(name_panel, True)
    panel.set_read_only(False)
    panel.run_command('append', {'characters': text})
    panel.set_syntax_file(syntax)
    panel.set_read_only(True)
    return panel


def kill_panel(name_panel='Rsb_parse_panel'):
    sublime.active_window().destroy_output_panel(name_panel)
