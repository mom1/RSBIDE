# -*- coding: utf-8 -*-
# @Author: mom1
# @Date:   2016-08-09 13:11:25
# @Last Modified by:   mom1
# @Last Modified time: 2016-08-10 00:20:55
import sublime
import re
# import RSBIDE.common.path as Path
from RSBIDE.common.verbose import log
from RSBIDE.common.config import config
from RSBIDE.RsbIde_print_panel import get_panel

ID = 'Linter'
global all_regions
all_regions = []


def run_all_lint(view, ProjectManager):
    global all_regions
    project = ProjectManager.get_current_project()
    window = sublime.active_window()
    erase_all_regions(view)
    LongLines(view, ProjectManager)
    comment_code(view, ProjectManager)
    vare_unused(view, ProjectManager)
    if project.get_setting("SHOW_SAVE", True):
        all_regions = [['Слишком длинная строка', view.rowcol(i.a)] for i in view.get_regions('LongLines')]
        all_regions += [['Закомментированный код', view.rowcol(i.a)] for i in view.get_regions('comment_code')]
        all_regions += [['Не используемая переменная ' + view.substr(i), view.rowcol(i.a)] for i in view.get_regions('vare_unused')]
        all_regions = sorted(all_regions, key=lambda x: x[1][0])
        all_regions = [[i[0], str([j + 1 for j in i[1]])] for i in all_regions]
        window.show_quick_panel(all_regions, _on_done, 0, 0, lambda x: _on_done(x))


def _on_done(item):
    global all_regions
    if item == -1:
        return
    window = sublime.active_window()
    row = int(all_regions[item][1].split(', ')[0].strip('[')) - 1
    col = int(all_regions[item][1].split(', ')[1].strip(']')) - 1
    pt = window.active_view().text_point(row, col)
    window.active_view().sel().clear()
    window.active_view().sel().add(sublime.Region(pt))
    window.active_view().show_at_center(pt)


def erase_all_regions(view):
    view.erase_regions("LongLines")
    view.erase_regions("comment_code")
    view.erase_regions("vare_unused")


def LongLines(view, ProjectManager):
        #  Settings  #
        project = ProjectManager.get_current_project()
        maxLength = project.get_setting("MAXLENGTH", 150)
        islint = project.get_setting("LINT", False)
        scope = "invalid.mac"
        firstCharacter_Only = False
        if not islint:
            return

        if 'R-Style' not in view.settings().get('syntax'):
            return
        view.erase_regions("LongLines")
        indentationSize = view.settings().get("tab_size")
        document = sublime.Region(0, view.size())
        lineRegions = view.lines(document)
        invalidRegions = []
        for region in lineRegions:
            text = view.substr(region)
            text_WithoutTabs = text.expandtabs(indentationSize)
            if text_WithoutTabs.isspace():
                tabOffset = 0
            else:
                tabDifference = len(text_WithoutTabs) - len(text)
                tabOffset = tabDifference
            lineLength = (region.end() - region.begin()) - tabOffset
            if lineLength > maxLength:
                highlightStart = region.begin() + (maxLength - tabOffset)
                if firstCharacter_Only is True:
                    highlightEnd = highlightStart + 1
                else:
                    highlightEnd = region.end()
                invalidRegion = sublime.Region(highlightStart, highlightEnd)
                invalidRegions.append(invalidRegion)
        if len(invalidRegions) > 0:
            view.add_regions("LongLines", invalidRegions, scope)


def comment_code(view, ProjectManager):
    project = ProjectManager.get_current_project()
    islint = project.get_setting("LINT", False)
    if not islint:
        return
    pref = 'RSBIDE:Lint_'
    l_comment = [(view.substr(i).rstrip('\r\n') + "\n", i) for i in view.find_by_selector('source.mac comment. - punctuation.definition.comment.mac')]
    scope = "invalid.mac"
    invalidRegions = []
    for x in l_comment:
        parse_panel = get_panel(sublime.active_window().active_view(), "".join(x[0]), name_panel=pref + 'comment_code')
        if len(parse_panel.find_by_selector(
                'meta.class.mac, meta.macro.mac, meta.variable.mac, meta.if.mac, meta.while.mac, meta.for.mac, meta.const.mac')) > 0:
            invalidRegions.append(x[1])
    sublime.active_window().destroy_output_panel(pref + 'comment_code')
    if len(invalidRegions) > 0:
        view.add_regions("comment_code", invalidRegions, scope)


def vare_unused(view, ProjectManager):
    project = ProjectManager.get_current_project()
    islint = project.get_setting("LINT", False)
    if not islint:
        return
    # pref = 'RSBIDE:Lint_'
    scope = "invalid.mac"
    invalidRegions = []
    l_all_vare = [(
        view.substr(i).rstrip('\r\n'), i) for i in view.find_by_selector('source.mac meta.macro.mac meta.variable.mac variable.declare.name.mac')]
    l_all_meta_macro = view.find_by_selector('meta.macro.mac')
    for x in l_all_vare:
        extract = []
        for j in l_all_meta_macro:
            if j.contains(x[1].a):
                extract = j
                break
        pattern = r'(\b%s\b)' % (x[0])
        m = re.findall(pattern, view.substr(extract), re.I)
        if not (len(m) - 1) > 0:
            invalidRegions.append(x[1])
    if len(invalidRegions) > 0:
        view.add_regions("vare_unused", invalidRegions, scope)
