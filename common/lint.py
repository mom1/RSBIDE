# -*- coding: utf-8 -*-
# @Author: mom1
# @Date:   2016-08-09 13:11:25
# @Last Modified by:   mom1
# @Last Modified time: 2018-04-13 17:19:49
import re
import sublime
import threading
import RSBIDE.common.settings as Settings
from RSBIDE.common.notice import *
from RSBIDE.common.async import run_after_loading
from RSBIDE.common.RsbIde_print_panel import get_panel, kill_panel

ID = 'Linter'


class Linter(threading.Thread):
    """docstring for Linter"""

    _request_id_lock = threading.Lock()

    def __init__(self, view, force=False):
        threading.Thread.__init__(self)

        self.view = view
        self.all_regions = []
        rsb_settings = Settings.proj_settings
        self.settings = rsb_settings
        if not self.settings:
            log('Init', 'Нет настроек')
            return
        self.scope = self.settings.get("SCOP_ERROR", "invalid.mac")
        self.flags = sublime.DRAW_NO_FILL
        self.force = force

    def run(self):
        if not self.settings:
            log('Run', 'Нет настроек')
            return
        log('Run')
        window = sublime.active_window()
        islint = self.settings.get("LINT", True)
        if not islint or not self.is_RStyle_view():
            return
        self.erase_all_regions()
        self.LongLines()
        self.comment_code()
        self.vare_unused()
        self.empty_line()
        self.many_param()
        self.many_dept_loop()
        self.cpwin()
        self.unknown_prefix_variable()
        self.all_comment = [(self.get_text_lint(i), j) for i in self.all_lint_regions() for j in self.view.get_regions(i)]
        count_comment = len(self.all_comment)
        sublime.status_message("Проверка на замечания выполнена: найденно %s" % (count_comment))
        if self.settings.get("SHOW_SAVE", True) or self.force:
            self.all_regions = [[i[0], self.view.rowcol(i[1].begin())] for i in self.all_comment]
            self.all_regions = sorted(self.all_regions, key=lambda x: x[1][0])
            self.all_comment = sorted(self.all_comment, key=lambda x: x[1].begin())
            self.all_regions = [[i[0], str([j + 1 for j in i[1]])] for i in self.all_regions]
            window.show_quick_panel(self.all_regions, self._on_done, sublime.KEEP_OPEN_ON_FOCUS_LOST, 0, lambda x: self._on_done(x, True))

    def _on_done(self, item, hig=False):
        def add_reg():
            if row == 0 and 'col' == 0:
                return
            dec_reg = self.all_comment[item][1]
            view.add_regions('rsbide_curlint', [dec_reg], 'string', 'dot', sublime.DRAW_NO_FILL)

        def clear_reg():
            view.erase_regions('rsbide_curlint')

        window = sublime.active_window()
        view = window.active_view()
        if not hig:
            run_after_loading(view, clear_reg)

        if item == -1:
            clear_reg()
            return
        row = int(self.all_regions[item][1].split(', ')[0].strip('[')) - 1
        col = int(self.all_regions[item][1].split(', ')[1].strip(']')) - 1
        pt = view.text_point(row, col)
        add_reg()
        view.sel().clear()
        view.sel().add(sublime.Region(pt))
        view.show_at_center(pt)

    def get_text_lint(self, key):
        ''' Тексты проверок '''
        if key is None:
            return ''
        lint_mess = {
            'LongLines': 'Слишком длинная строка',
            'comment_code': 'Закомментированный код',
            'vare_unused': 'Не используемая переменная',
            'empty_line': 'Много предшествующих пустых строк',
            'not_empty_line': 'Ожидается 1 пустая строка',
            'many_param': 'У функции слишком много параметров',
            'reg_loop': 'Большая вложенность циков и условий',
            'reg_loop_for': 'Критическая вложенность for',
            'cpwin': 'Не указана cpwin',
            'unknown_prefix_variable': 'Неизвестный префикс переменной'
        }
        return lint_mess.get(key, '')

    def all_lint_regions(self):
        ''' Перечень всех проверок '''
        return [
            'LongLines', 'comment_code', 'vare_unused',
            'empty_line', 'not_empty_line', 'many_param',
            'reg_loop_for', 'reg_loop', 'cpwin',
            'unknown_prefix_variable'
        ]

    def erase_all_regions(self):
        ''' Очистка всех подсвеченых проверок '''
        for i in self.all_lint_regions():
            self.view.erase_regions(i)
        self.view.erase_regions('rsbide_curlint')

    def is_RStyle_view(self, locations=None):
        view = self.view
        return (
            ('RStyle' in view.settings().get('syntax')) or ('R-Style' in view.settings().get('syntax')) or
            (locations and len(locations) and '.mac' in view.scope_name(locations[0])))

    def LongLines(self):
        ''' Проверка на длинные строки '''
        maxLength = self.settings.get("MAXLENGTH", 160)
        scope = self.scope
        firstCharacter_Only = False
        log('LongLines')
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
        ''' Проверка на закомментированный код '''
        pref = 'RSBIDE:Lint_'
        log('comment_code')
        l_comment = [
            (self.view.substr(i).rstrip('\r\n') + "\n", i) for i in self.view.find_by_selector('source.mac comment. - punctuation.definition.comment.mac')]
        scope = self.scope
        invalidRegions = []
        for x in l_comment:
            parse_panel = get_panel(sublime.active_window().active_view(), "".join(x[0]), name_panel=pref + 'comment_code')
            not_empty_line = sublime.Region(0, 0)
            for l in parse_panel.lines(sublime.Region(0, parse_panel.size())):
                if not re.match(r'^(\s)*$', parse_panel.substr(l), re.IGNORECASE):
                    not_empty_line = l
                    break
            if re.match(r'^\s*(example|пример|description)', parse_panel.substr(not_empty_line), re.IGNORECASE):
                continue
            if len(parse_panel.find_by_selector(
                    'meta.class.mac, meta.macro.mac, meta.variable.mac, meta.if.mac, meta.while.mac, meta.for.mac, meta.const.mac')) > 0:
                invalidRegions.append(x[1])
        kill_panel(pref + 'comment_code')
        if len(invalidRegions) > 0:
            self.view.add_regions("comment_code", invalidRegions, scope, flags=self.flags)

    def vare_unused(self):
        ''' Проверка на не используемые переменные '''
        log('vare_unused')
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
        ''' Проверка пустых строк '''
        log('empty_line')
        max_eline = self.settings.get("MAX_EMPTY_LINE", 2)
        mr = self.view.find_all(r'^(\s)*$')
        invalidRegions = []
        invalidExpect = []
        for x in mr:
            if len(self.view.lines(self.view.full_line(x))) > max_eline:
                invalidRegions += [self.view.line(x.b + 1)]
        cm = self.view.find_by_selector('storage.type.class.mac, storage.type.macro.mac')
        for x in cm:
            prev_line = self.view.line(self.view.line(x.a).a - 1)
            if not re.match(r'^(\s)*$', self.view.substr(prev_line), re.IGNORECASE):
                invalidExpect += [self.view.line(x.a)]
        if len(invalidRegions) > 0:
            self.view.add_regions("empty_line", invalidRegions, self.scope, flags=self.flags)
        if len(invalidExpect) > 0:
            self.view.add_regions("not_empty_line", invalidExpect, self.scope, flags=self.flags)

    def many_param(self):
        ''' Проверка количества параметров '''
        log('many_param')
        max_count_param = self.settings.get("MAX_COUNT_MACRO_PARAM", 5)
        macroRegsName = self.view.find_by_selector('meta.macro.mac & (storage.type.macro.mac, entity.name.function.mac, variable.parameter.macro.mac)')
        invalidRegions = []
        param = []
        for x in macroRegsName:
            if self.view.substr(x).lower() == 'macro':
                if len(param) > max_count_param:
                    lines = self.view.lines(param[-1])
                    invalidRegions += [sublime.Region(param[0].a, lines[-1].b)]
                param = []
            elif 'variable.parameter.macro.mac' in self.view.scope_name(x.a):
                    param += [x]
        if len(invalidRegions) > 0:
            self.view.add_regions("many_param", invalidRegions, self.scope, flags=self.flags)

    def many_dept_loop(self):
        ''' Проверка уровня вложенности '''
        log('many_dept_loop')
        max_depth = self.settings.get("MAX_DEPTH_LOOP", 3)
        reg_loop = self.view.find_by_selector('source.mac' + ' meta.if.mac' * max_depth)
        reg_loop += self.view.find_by_selector('source.mac' + ' meta.while.mac' * max_depth)
        if len(reg_loop) > 0:
            self.view.add_regions("reg_loop", reg_loop, self.scope, flags=self.flags)

    def cpwin(self):
        ''' Проверка наличия cpwin '''
        log('cpwin')
        l_cpwin = self.view.find_by_selector('keyword.control.cpwin.mac')
        if len(l_cpwin) == 0:
            invalidRegions = [self.view.line(sublime.Region(0, 0))]
            self.view.add_regions("cpwin", invalidRegions, self.scope, flags=self.flags)

    def unknown_prefix_variable(self):
        ''' Проверка префиксов переменных '''
        log('unknown_prefix_variable')

        pref_g = self.settings.get("PREFIX_VARIABLE_GLOBAL")
        pref_visual = self.settings.get("PREFIX_VARIABLE_VISUAL")
        pref_type = self.settings.get("PREFIX_VARIABLE_TYPE")
        if len(pref_type) > 0 and len(pref_visual) > 0:
            pref_visual += r'|'
        s_reg_exp = '^%s%s' % (pref_visual, pref_type)
        all_variable = self.view.find_by_selector('variable.declare.name - meta.const.mac')
        know_vars = []
        invalidRegions = []
        for x in all_variable:
            stext = self.view.substr(x)
            if len(stext) == 1:
                know_vars.append(self.view.substr(x))
                continue
            stext = re.sub(r'^' + pref_g, '', stext, re.IGNORECASE | re.VERBOSE)
            if re.match(s_reg_exp, stext, re.IGNORECASE | re.VERBOSE):
                know_vars.append(self.view.substr(x))
        invalidRegions = [i for i in all_variable if self.view.substr(i) not in know_vars]
        if len(invalidRegions) > 0:
            self.view.add_regions("unknown_prefix_variable", invalidRegions, self.scope, flags=self.flags)
