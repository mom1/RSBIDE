# -*- coding: utf-8 -*-
# @Author: mom1
# @Date:   2016-08-09 13:11:25
# @Last Modified by:   MOM
# @Last Modified time: 2016-08-11 01:15:20
import sublime
import re
import threading
from RSBIDE.RsbIde_print_panel import get_panel
# from RSBIDE.common.verbose import log

ID = 'Linter'


class Linter(threading.Thread):
    """docstring for Linter"""

    def __init__(self, view, ProjectManager=None):
        threading.Thread.__init__(self)

        self.view = view
        self.all_regions = []
        self.ProjectManager = ProjectManager
        self.scope = self.ProjectManager.get_current_project().get_setting("SCOP_ERROR", "invalid.mac")
        self.flags = sublime.DRAW_NO_FILL

    def run(self):
        project = self.ProjectManager.get_current_project()
        window = sublime.active_window()
        islint = project.get_setting("LINT", True)
        if not islint or not self.is_RStyle_view():
            return
        self.erase_all_regions()
        self.LongLines()
        self.comment_code()
        self.vare_unused()
        self.empty_line()
        if project.get_setting("SHOW_SAVE", True):
            self.all_regions = [[self.get_text_lint(i), self.view.rowcol(j.a)] for i in self.all_lint_regions() for j in self.view.get_regions(i)]
            self.all_regions = sorted(self.all_regions, key=lambda x: x[1][0])
            self.all_regions = [[i[0], str([j + 1 for j in i[1]])] for i in self.all_regions]
            window.show_quick_panel(self.all_regions, self._on_done, 0, 0, lambda x: self._on_done(x))

    def _on_done(self, item):
        if item == -1:
            return
        window = sublime.active_window()
        view = window.active_view()
        row = int(self.all_regions[item][1].split(', ')[0].strip('[')) - 1
        col = int(self.all_regions[item][1].split(', ')[1].strip(']')) - 1
        pt = view.text_point(row, col)
        view.sel().clear()
        view.sel().add(sublime.Region(pt))
        view.show_at_center(pt)

    def get_text_lint(self, key):
        if key is None:
            return ''
        lint_mess = {
            'LongLines': 'Слишком длинная строка',
            'comment_code': 'Закомментированный код',
            'vare_unused': 'Не используемая переменная',
            'empty_line': 'Много предшествующих пустых строк'
        }
        return lint_mess.get(key, '')

    def all_lint_regions(self):
        return ['LongLines', 'comment_code', 'vare_unused', 'empty_line']

    def erase_all_regions(self):
        for i in self.all_lint_regions():
            self.view.erase_regions(i)

    def is_RStyle_view(self, locations=None):
        view = self.view
        return (
            ('RStyle' in view.settings().get('syntax')) or ('R-Style' in view.settings().get('syntax')) or
            (locations and len(locations) and '.mac' in view.scope_name(locations[0])))

    def LongLines(self):
            #  Settings  #
            project = self.ProjectManager.get_current_project()
            maxLength = project.get_setting("MAXLENGTH", 150)
            islint = project.get_setting("LINT", False)
            scope = self.scope
            firstCharacter_Only = False
            if not islint:
                return

            if 'R-Style' not in self.view.settings().get('syntax'):
                return
            indentationSize = self.view.settings().get("tab_size")
            document = sublime.Region(0, self.view.size())
            lineRegions = self.view.lines(document)
            invalidRegions = []
            for region in lineRegions:
                text = self.view.substr(region)
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
                self.view.add_regions("LongLines", invalidRegions, scope, flags=self.flags)

    def comment_code(self):
        project = self.ProjectManager.get_current_project()
        islint = project.get_setting("LINT", False)
        if not islint:
            return
        pref = 'RSBIDE:Lint_'
        l_comment = [
            (self.view.substr(i).rstrip('\r\n') + "\n", i) for i in self.view.find_by_selector('source.mac comment. - punctuation.definition.comment.mac')]
        scope = self.scope
        invalidRegions = []
        for x in l_comment:
            parse_panel = get_panel(sublime.active_window().active_view(), "".join(x[0]), name_panel=pref + 'comment_code')
            if len(parse_panel.find_by_selector(
                    'meta.class.mac, meta.macro.mac, meta.variable.mac, meta.if.mac, meta.while.mac, meta.for.mac, meta.const.mac')) > 0:
                invalidRegions.append(x[1])
        sublime.active_window().destroy_output_panel(pref + 'comment_code')
        if len(invalidRegions) > 0:
            self.view.add_regions("comment_code", invalidRegions, scope, flags=self.flags)

    def vare_unused(self):
        project = self.ProjectManager.get_current_project()
        islint = project.get_setting("LINT", False)
        if not islint:
            return
        # pref = 'RSBIDE:Lint_'
        scope = self.scope
        invalidRegions = []
        l_all_vare_macro = [(
            self.view.substr(i).rstrip('\r\n'), i) for i in self.view.find_by_selector('source.mac meta.macro.mac meta.variable.mac variable.declare.name.mac')]
        l_all_vare_class = [(
            self.view.substr(i).rstrip('\r\n'), i)
            for i in self.view.find_by_selector('source.mac meta.class.mac meta.variable.mac variable.declare.name.mac - meta.macro.mac')]

        l_all_meta_macro = self.view.find_by_selector('meta.macro.mac')
        l_all_meta_class = self.view.find_by_selector('meta.class.mac')
        l_all_meta_class = [c for c in l_all_meta_class for m in l_all_meta_macro if c.contains(m)]
        for x in l_all_vare_macro:
            extract = []
            for j in l_all_meta_macro:
                if j.contains(x[1].a):
                    extract = j
                    break
            pattern = r'(\b%s\b)' % (x[0])
            m = re.findall(pattern, self.view.substr(extract), re.I)
            if not (len(m) - 1) > 0:
                invalidRegions.append(x[1])
        for x in l_all_vare_class:
            extract = []
            for j in l_all_meta_class:
                if j.contains(x[1].a) and 'esc' not in self.view.substr(x[1]).lower():
                    extract = j
                    break
            pattern = r'(\b%s\b)' % (x[0])
            if len(extract) > 0:
                m = re.findall(pattern, self.view.substr(extract), re.I)
                if not (len(m) - 1) > 0:
                    invalidRegions.append(x[1])
        if len(invalidRegions) > 0:
            self.view.add_regions("vare_unused", invalidRegions, scope, flags=self.flags)

    def empty_line(self):
        mr = self.view.find_all(r'^(\s)*$')
        max_eline = self.ProjectManager.get_current_project().get_setting("MAX_EMPTY_LINE", 2)
        invalidRegions = []
        for x in mr:
            if len(self.view.lines(self.view.full_line(x))) > max_eline:
                invalidRegions += [self.view.line(x.b + 1)]
        if len(invalidRegions) > 0:
            self.view.add_regions("empty_line", invalidRegions, self.scope, flags=self.flags)
