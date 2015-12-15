# coding=cp1251
# -------------
import sublime

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
        name_panel = 'Rsb_panel_log'
    elif bDoc:
        name_panel = 'Rsb_panel_doc'
    else:
        name_panel = 'Rsb_panel'

    if b_overwrite or not output_view:
        panel = view.window().create_output_panel(name_panel)
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
    if region_mark:
        # print(region_mark)
        # flags = sublime.DRAW_NO_FILL
        # region = panel.word(panel.text_point(showline, region_mark[1]))
        # print(region)
        # region = panel.expand_by_class(panel.text_point(showline-1, 0)-1, sublime.CLASS_WORD_START | sublime.CLASS_WORD_END)
        # panel.add_regions(
        #     name_panel, region, 'string', 'dot', flags)
        pass

    panel.show_at_center(panel.line(panel.text_point(showline-1, 0)-1))
    panel.set_read_only(True)
    view.window().run_command("show_panel", {"panel": "output.%s" % name_panel})


def get_panel(view, text, b_overwrite=True, bLog=False):
    panel = view.window().create_output_panel('Rsb_parse_panel')
    panel.set_read_only(False)
    panel.run_command('append', {'characters': text})

    panel.set_syntax_file(view.settings().get('syntax'))

    panel.set_read_only(True)
    return panel
