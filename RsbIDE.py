# -*- coding: utf-8 -*-
# @Author: Maximus
# @Date:   2018-03-19 19:08:39
# @Last Modified by:   mom1
# @Last Modified time: 2018-04-27 11:19:28
import sublime
import sublime_plugin
import os
import time
import re
import json
import hashlib
import imp
import Default.history_list as History
import RSBIDE.external.symdb as symdb
import RSBIDE.common.ast_rsl as ast_rsl
import RSBIDE.common.settings as Settings
from subprocess import call
from RSBIDE.common.notice import *
from RSBIDE.common.tree import Tree
from RSBIDE.common.lint import Linter
from RSBIDE.common.config import config
from RSBIDE.common.RsbIde_print_panel import print_to_panel
from RSBIDE.common.async import async_worker, run_after_loading

ST2 = int(sublime.version()) < 3000

if ST2:
    try:
        sublime.error_message("RSBIDE Package Message:\n\nЭтот Пакет НЕ РАБОТАЕТ в Sublime Text 2 \n\n Используйте Sublime Text 3.")
    except Exception as e:
        try:
            sublime.message_dialog("RSBIDE Package Message:\n\nЭтот Пакет НЕ РАБОТАЕТ в Sublime Text 2 \n\n Используйте Sublime Text 3.")
        except Exception as e:
            pass


def posix(path):
    return path.replace("\\", "/")


def is_file_index(file):
    ret = False
    if file and file.endswith('.mac'):
        ret = True
    elif file and file.endswith('.xml'):
        ret = True
    return ret


def is_RStyle_view(view):
    if ('R-Style' in view.settings().get('syntax')):
        return True
    elif is_file_index(view.file_name()):
        return True
    else:
        return False


def get_db(window):
    if len(window.folders()) == 0:
        return []
    fold = window.folders()[0]
    sublime_cache_path = sublime.cache_path()
    tmp_folder = sublime_cache_path + "/RSBIDE/"
    if os.path.isdir(tmp_folder) is False:
        log('Папка не найдена. Создаем папку кэша: %s' % tmp_folder)
        os.makedirs(tmp_folder)
    hsh = hashlib.md5(fold.encode('utf-8'))
    db = [os.path.join(tmp_folder, hsh.hexdigest() + '.cache_db')]
    return db


def extent_reg(view, sel, mod=1):
    if mod == 1:  # class
        dist_scope = 'source.mac meta.class.mac'
        dist_scope_name = 'source.mac meta.class.mac entity.name.class.mac'
    elif mod == 2:  # macro
        dist_scope = 'source.mac meta.macro.mac'
        dist_scope_name = 'source.mac meta.macro.mac entity.name.function.mac'
    regions = [i for i in view.find_by_selector(dist_scope) if i.contains(sel)]
    if len(regions) == 0:
        return None
    region = regions[-1]
    regions_name = [j for j in view.find_by_selector(dist_scope_name) if region.contains(j)]
    region_name = regions_name[-1]
    return (region, region_name)


def get_result(view, symbol):

    def ret_format(file=view.file_name(), row=0, col=0, scope='', rowcol=None):
        if isinstance(rowcol, tuple):
            row, col = rowcol
        return {'file': file, 'row': row, 'col': col, 'scope': scope}

    window = sublime.active_window()
    sel = view.sel()[0]
    if sel.empty():
        sel = view.word(sel)
    if not symbol:
        symbol = view.substr(sel).strip()

    t = time.time()
    if symbol.lower() == 'end' and view.match_selector(
        sel.begin(),
        'keyword.macro.end.mac, keyword.class.end.mac, keyword.if.end.mac, keyword.for.end.mac, keyword.while.end.mac'
    ):
        meta = view.extract_scope(sel.begin() - 1)
        res = ret_format(rowcol=view.rowcol(meta.begin()))
        return [res]
    elif view.match_selector(sel.begin(), 'import.file.mac'):
        return [ret_format(f) for f in symdb.query_packages_info(symbol.lower())]
    elif view.match_selector(sel.begin(), 'entity.other.inherited-class.mac'):
        ret = window.lookup_symbol_in_index(symbol)
        return [ret_format(cp[0], cp[2][0] - 1, cp[2][1] - 1) for cp in ret]

    # контекст
    cur_class = extent_reg(view, sel)
    cur_macro = extent_reg(view, sel, 2)
    log('Тек. контекст', "%.3f" % (time.time() - t))
    t = time.time()
    # Готовим генераторы
    g_all = ast_rsl.generat_scope(
        view,
        'variable.declare.name.mac - (meta.class.mac, meta.macro.mac), entity.name.function.mac - meta.class.mac, entity.name.class.mac'
    )
    cls_symbols = ast_rsl.generat_scope(
        view,
        'meta.class.mac variable.declare.name.mac - meta.macro.mac, meta.class.mac entity.name.function.mac - (meta.macro.mac meta.macro.mac)'
    )
    cls_param_symbols = ast_rsl.generat_scope(view, 'variable.parameter.class.mac')
    macro_symbols = ast_rsl.generat_scope(
        view,
        'meta.macro.mac & (variable.parameter.macro.mac, variable.declare.name.mac, meta.macro.mac meta.macro.mac entity.name.function.mac)'
    )
    log('Подготовка генераторов', "%.3f" % (time.time() - t))
    t = time.time()
    # Глобал в текущем файле
    for ga in g_all:
        if view.substr(ga).lower() == symbol.lower():
            log('Глобал в текущем файле', "%.3f" % (time.time() - t))
            return [ret_format(rowcol=view.rowcol(ga.begin()))]

    # В текущем классе
    if cur_class:
        for cs in cls_symbols:
            if cur_class[0].contains(cs) and view.substr(cs).lower() == symbol.lower():
                if cur_macro and view.substr(cur_macro[1]).lower() == symbol.lower():
                    break
                log('В текущем классе', "%.3f" % (time.time() - t))
                return [ret_format(rowcol=view.rowcol(cs.begin()))]
        # В параметрах класса
        if cur_macro is None:
            for cps in cls_param_symbols:
                if cur_class[0].contains(cps) and view.substr(cps).lower() == symbol.lower():
                    log('В параметрах класса', "%.3f" % (time.time() - t))
                    return [ret_format(rowcol=view.rowcol(cps.begin()))]
    # В текущем макро
    if cur_macro:
        for ms in macro_symbols:
            if cur_macro[0].contains(ms) and view.substr(ms).lower() == symbol.lower():
                log('В текущем макро', "%.3f" % (time.time() - t))
                return [ret_format(rowcol=view.rowcol(ms.begin()))]

    # В родителях
    if cur_class:
        find_symbols = symdb.query_parent_symbols_go(view.substr(cur_class[1]), symbol)
        if find_symbols and len(find_symbols) > 0:
            log('В родителях', "%.3f" % (time.time() - t))
            return find_symbols

    # В Глобальном глобале
    ret = symdb.query_globals_in_packages_go(symdb.get_package(view.file_name()), symbol)
    log('В Глобальном глобале', "%.3f" % (time.time() - t))
    return ret


class GoToDefinitionCommand(sublime_plugin.WindowCommand):
    window = sublime.active_window()

    def run(self):
        view = self.window.active_view()
        self.view = view
        if not is_RStyle_view(view):
            return
        sel = self.view.sel()[0]
        if sel.empty():
            sel = view.word(sel)
        symbol = view.substr(sel).strip()
        self.old_view = self.window.active_view()
        self.curr_loc = sel.begin()
        History.get_jump_history(self.window.id()).push_selection(view)
        self.search(symbol)

    def search(self, symbol):

        def async_search():
            if not update_settings():
                return
            results = get_result(self.view, symbol)
            handle_results(results)

        def handle_results(results):
            if len(results) > 1:
                self.ask_user_result(results)
            elif results:  # len(results) == 1
                self.goto(results[0])
            else:
                sublime.status_message('Symbol "{0}" not found'.format(symbol))
        sublime.set_timeout_async(async_search, 10)

    def ask_user_result(self, results):
        view = self.window.active_view()
        self.view = view
        self.last_viewed = None

        def on_select(i, trans=False):

            def add_reg():
                if results[i]['row'] == 0 and results[i]['col'] == 0:
                    return
                p = v.text_point(results[i]['row'], results[i]['col'])
                dec_reg = v.word(p)
                v.add_regions('rsbide_declare', [dec_reg], 'string', 'dot', sublime.DRAW_NO_FILL)

            def clear_reg():
                v.erase_regions('rsbide_declare')

            flags = sublime.ENCODED_POSITION if not trans else sublime.ENCODED_POSITION | sublime.TRANSIENT
            if self.last_viewed:
                self.last_viewed.erase_regions('rsbide_declare')
            if i > -1:
                v = self.goto(results[i], flags)
                self.last_viewed = v
                if trans:
                    run_after_loading(v, add_reg)
                else:
                    run_after_loading(v, clear_reg)
            else:
                self.window.focus_view(self.old_view)
                self.old_view.show_at_center(self.curr_loc)

        self.view.window().show_quick_panel(
            list(map(self.format_result, results)),
            on_select,
            sublime.KEEP_OPEN_ON_FOCUS_LOST,
            0,
            lambda x: on_select(x, True)
        )

    def goto(self, result, flags=sublime.ENCODED_POSITION):
        return self.view.window().open_file(
            '{0}:{1}:{2}'.format(
                result['file'],
                result['row'] + 1,
                result['col'] + 1
            ),
            flags
        )

    def format_result(self, result):
        rel_path = os.path.relpath(result['file'], self.view.window().folders()[0])
        desc = result['scope']
        if '.' in result['scope']:
            desc = '{0} ({1})'.format(*result['scope'].split('.'))
        return [
            '{0} ({1})'.format(rel_path, result['row']),
            desc
        ]

    def is_visible(self):
        return is_RStyle_view(self.window.active_view())

    def description(self):
        return 'RSBIDE: Перейти к объявлению\talt+g'


class PrintSignToPanelCommand(sublime_plugin.WindowCommand):

    def run(self):
        view = self.window.active_view()
        self.view = view
        self.db_doc = None
        if not is_RStyle_view(view):
            return
        sel = self.view.sel()[0]
        if sel.empty():
            sel = view.word(sel)
        symbol = view.substr(sel).strip()
        self.search(symbol)

    def search(self, symbol):

        def async_search():
            if not update_settings():
                return
            results = get_result(self.view, symbol)
            handle_results(results)

        def handle_results(results):
            if results:
                self.print_symbol(results[0])
            elif self.find_in_doc(symbol):
                self.print_symbol_doc(self.get_doc(symbol))
            else:
                sublime.status_message('Symbol "{0}" not found'.format(symbol))
        sublime.set_timeout_async(async_search, 10)

    def print_symbol(self, result):
        if result['file'].lower() == self.view.file_name().lower():
            source = self.view.substr(sublime.Region(0, self.view.size()))
        else:
            source = open(result['file'], encoding='Windows 1251').read()
        print_to_panel(self.view, source, showline=result['row'], region_mark=(result['row'], result['col']))

    def print_symbol_doc(self, doc_string):
        if not doc_string:
            return
        print_to_panel(self.view, doc_string, bDoc=True)

    def get_db_doc(self, symbol):
        lang = 'mac'
        path_db = os.path.dirname(
            os.path.abspath(__file__)) + "/dbHelp/%s.json" % lang
        if not self.db_doc:
            if os.path.exists(path_db):
                self.db_doc = json.load(open(path_db))
            else:
                return

        return self.db_doc.get(symbol.lower())

    def find_in_doc(self, symbol):
        return self.get_db_doc(symbol)

    def get_doc(self, symbol):
        found = self.get_db_doc(symbol)
        if found:
            menus = []

            # Title
            menus.append("Документация " + found["name"] + "\n" + "=" * max(len("Документация " + found["name"]), 40) + "\n")

            # Syntax
            menus.append(found["syntax"] + "\n")

            # Parameters
            for parameter in found["params"]:
                menus.append(
                    "\t- " + parameter["name"] + ": " + parameter["descr"] + "\n")

            # Description
            menus.append("\n" + found["descr"] + "\n")
            return ''.join(menus)
        else:
            return None

    def is_visible(self):
        return is_RStyle_view(self.window.active_view())

    def description(self):
        return 'RSBIDE: Показать область объявления\talt+s'


class RSBIDEListener(sublime_plugin.EventListener):

    previous_window = None
    previous_project = None

    def index_view(self, view):
        if not is_file_index(view.file_name()):
            return
        db = get_db(view.window())
        self.async_index_view(view.file_name(), db, view.window().folders())

    @staticmethod
    def async_index_view(file_name, databases, project_folders):

        if not update_settings():
            return

        for dbi, database in enumerate(databases):
            symdb.process_file(dbi, file_name)
            log('Indexed', file_name)
            symdb.commit()

    def on_post_save_async(self, view):
        self.index_view(view)
        if Settings.proj_settings.get("LINT_ON_SAVE", True):
            lint = Linter(view)
            lint.start()

    def on_modified_async(self, view):
        Linter(view).erase_all_regions()

    def on_activated(self, view):
        window = view.window()
        db = get_db(view.window())
        if not window:
            return False

        if self.previous_project != db:
            if self.previous_project is not None:
                if not update_settings():
                    return
                view.window().run_command('rebuild_cache', {'action': 'update'})
                self.previous_window = sublime.active_window().id()
            self.previous_project = db
        elif self.previous_window is not sublime.active_window().id():
            self.previous_window = sublime.active_window().id()
            if not update_settings():
                return
            view.window().run_command('rebuild_cache', {'action': 'update'})

    def intelige_end(self, view):
        result = []
        scope = view.scope_name(view.sel()[0].begin())
        if scope.strip().endswith('meta.if.mac') or scope.strip().endswith('meta.for.mac') or scope.strip().endswith('meta.while.mac'):
            result = [('end\trsl', 'end;')]
        elif scope.strip().endswith('meta.macro.mac'):
            result = [('End\trsl', 'End;')]
        elif scope.strip().endswith('meta.class.mac'):
            result = [('END\trsl', 'END;')]
        return result

    def on_query_completions(cls, view, prefix, locations):
        if len(locations) != 1:
            return []
        if not is_file_index(view.file_name()):
            return []

        if not update_settings():
            return
        completions = []
        sel = view.sel()[0]
        t = time.time()
        cur_class = extent_reg(view, sel)
        cur_macro = extent_reg(view, sel, 2)
        log('Тек. контекст', "%.3f" % (time.time() - t))
        if cur_class:
            completions = [('this\tclass', 'this')]

        if view.match_selector(
            sel.begin() - 1,
            'variable.declare.name.mac, entity.name.class.mac' +
            ', entity.name.function.mac, variable.parameter.macro.mac, variable.parameter.class.mac'
        ):
            return ([], sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
        elif view.match_selector(sel.begin() - 1, 'macro-param.mac, class-param.mac'):
            return list(cls.get_completions_always(view))

        t = time.time()

        if 'init' in [view.substr(view.word(sel)).lower(), prefix.lower()] and view.match_selector(sel.begin(), 'source.mac meta.class.mac'):
            cls_parent = [parent for parent in view.find_by_selector('entity.other.inherited-class.mac') if cur_class[0].contains(parent)]
            if cls_parent and len(cls_parent) > 0:
                return (
                    [('Init' + view.substr(cls_parent[0]) + '\tparent', 'Init' + view.substr(cls_parent[0]))],
                    sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS
                )
        # Подсказка файлов
        elif view.match_selector(sel.begin(), 'source.mac & (meta.import.mac, punctuation.definition.import.mac)'):
            currImp = [view.substr(s).lower().strip() for s in view.find_by_selector('meta.import.mac import.file.mac')]
            if view.file_name():
                currImp += [os.path.splitext(os.path.basename(view.file_name().lower()))[0]]
            files = [(p + '\tFiles', p) for p in symdb.query_packages(prefix.lower(), case=True) if p.lower() not in currImp]
            log('Подсказка файлов', "%.3f" % (time.time() - t))
            return (files, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
        # Подсказка метаданных
        elif view.match_selector(sel.begin(), 'source.mac string.quoted.double.mac'):
            if view.match_selector(sel.begin(), 'string.quoted.sql.mac'):
                isbac = True
            else:
                isbac = False
            if view.substr(sel.begin() - 1) == '.':
                line = view.line(sel.begin())
                bef_symbols = sublime.Region(line.begin(), sel.begin())
                il = 3
                word = ''
                while bef_symbols.size() >= il:
                    if view.match_selector(sel.begin() - il, 'constant.other.table-name.mac'):
                        word = view.extract_scope(sel.begin() - il)
                        word = re.sub(r'(\\")', '', view.substr(word))
                        break
                    il += 1
                log('Подсказка метаданных 1', "%.3f" % (time.time() - t))
                return (symdb.query_metadata_object(word), sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
            else:
                log('Подсказка метаданных 2', "%.3f" % (time.time() - t))
                return (symdb.query_metadata(prefix, isbac), sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
        # Подсказка классов
        elif view.match_selector(sel.begin(), 'source.mac inherited-class.mac'):
            if cur_class:
                completions = [
                    (view.substr(s) + '\tclass', view.substr(s))
                    for s in view.find_by_selector('entity.name.class.mac') if view.substr(cur_class[1]) != view.substr(s)
                ]
            else:
                completions = [(view.substr(s) + '\tclass', view.substr(s)) for s in view.find_by_selector('entity.name.class.mac')]
            completions += symdb.query_globals_class(symdb.get_package(view.file_name()), prefix)
            log('Подсказка классов', "%.3f" % (time.time() - t))
            return (completions, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)

        t = time.time()
        if sel.begin() == sel.end():
            sel = view.word(sel)

        # Из текущего файла по контексту
        g_all = ast_rsl.generat_scope(
            view,
            'variable.declare.name.mac - (meta.class.mac, meta.macro.mac)'
        )
        all_g_macros = ast_rsl.generat_scope(view, 'meta.macro.mac - (meta.class.mac)')
        all_g_name_macros = ast_rsl.generat_scope(view, 'meta.macro.mac entity.name.function.mac - (meta.class.mac)')
        all_cls_vars = ast_rsl.generat_scope(view, 'meta.class.mac variable.declare.name.mac - (meta.macro.mac, meta.class.mac meta.class.mac)')
        g_macros = zip(all_g_macros, all_g_name_macros)
        all_cls_macros = ast_rsl.generat_scope(view, 'meta.class.mac meta.macro.mac')
        all_cls_macros_names = ast_rsl.generat_scope(view, 'meta.class.mac meta.macro.mac entity.name.function.mac')
        g_class_names = ast_rsl.generat_scope(view, 'meta.class.mac entity.name.class.mac')
        all_macro_params = ast_rsl.generat_scope(view, 'meta.macro.mac variable.parameter.macro.mac')
        all_macro_vars = ast_rsl.generat_scope(view, 'meta.macro.mac variable.declare.name.mac')
        all_g_param_macros = view.find_by_selector('variable.parameter.macro.mac - (meta.class.mac)')

        log('Подготовка генераторов', "%.3f" % (time.time() - t))
        t = time.time()
        for g in g_all:
            g_scop = 'global'
            if view.match_selector(g.begin(), 'meta.const.mac'):
                g_scop = 'const'
            elif view.match_selector(g.begin(), 'variable.declare.name.mac'):
                g_scop = 'var'
            completions += [(view.substr(g) + '\t' + g_scop, view.substr(g))]
        log('Глобал переменные', "%.3f" % (time.time() - t))

        t = time.time()
        for clsn in g_class_names:
            completions += [(view.substr(clsn) + '\t' + 'class', view.substr(clsn))]
        log('Глобал class', "%.3f" % (time.time() - t))
        t = time.time()
        for g_m in g_macros:
            g_param_macros = [gpm for gpm in all_g_param_macros if g_m[0].contains(gpm)]
            hint = ", ".join(["${%s:%s}" % (k + 1, view.substr(v).strip()) for k, v in enumerate(g_param_macros)])
            completions += [(view.substr(g_m[1]) + '\tmacro', view.substr(g_m[1]) + '(' + hint + ')')]
        log('Глобал macro', "%.3f" % (time.time() - t))

        t = time.time()
        cls_params = []
        if cur_class:
            cls_vars = [cv for cv in all_cls_vars if cur_class[0].contains(cv)]
            cls_macros = [cl for cl in all_cls_macros if cur_class[0].contains(cl)]
            cls_macros_names = [cmn for cmn in all_cls_macros_names if cur_class[0].contains(cmn)]
            gen_mac = zip(cls_macros, cls_macros_names)
            cls_params = [cp for cp in view.find_by_selector('meta.class.mac class-param.mac variable.parameter.class.mac') if cur_class[0].contains(cp)]
            log('Подготовка класса', "%.3f" % (time.time() - t))
            t = time.time()

            for cls_var in cls_vars:
                completions += [(view.substr(cls_var) + '\tvar in class', view.substr(cls_var))]
            log('Переменные класса', "%.3f" % (time.time() - t))
            t = time.time()

            for c_elem in gen_mac:
                param_macros = [gpm for gpm in view.find_by_selector('meta.class.mac variable.parameter.macro.mac') if c_elem[0].contains(gpm)]
                hint = ", ".join(["${%s:%s}" % (k + 1, view.substr(v).strip()) for k, v in enumerate(param_macros)])
                completions += [(view.substr(c_elem[1]) + '\tmacro in class', view.substr(c_elem[1]) + '(' + hint + ')')]
            log('Функции класса', "%.3f" % (time.time() - t))
            t = time.time()

        if cur_macro:
            cls_params = []
            param_macro = [(view.substr(pm) + '\tmacro param', view.substr(pm)) for pm in all_macro_params if cur_macro[0].contains(pm)]
            vars_macro = [(view.substr(vm) + '\tvar in macro', view.substr(vm)) for vm in all_macro_vars if cur_macro[0].contains(vm)]
            completions += param_macro
            completions += vars_macro
            if cur_class and cur_class[0].contains(cur_macro[0]):
                pass
            else:
                pass
            log('Параметры текущего macro', "%.3f" % (time.time() - t))
            t = time.time()

        for cls_param in cls_params:
            completions += [(view.substr(cls_param) + '\tclass param', view.substr(cls_param))]
        log('Параметры текущего class', "%.3f" % (time.time() - t))
        t = time.time()

        # Из родителя, нужно именно тут т.к. сортировка
        if cur_class:
            completions += symdb.query_parent_symbols(view.substr(cur_class[1]), prefix)
            log('Из родителей', "%.3f" % (time.time() - t))
            t = time.time()

        # Умный End
        completions += cls.intelige_end(view)
        log('Умный End', "%.3f" % (time.time() - t))
        t = time.time()

        # Автокомплит
        completions += cls.get_completions_always(view)
        log('Автокомплит', "%.3f" % (time.time() - t))
        t = time.time()

        # Из глобала
        t = time.time()
        completions += symdb.query_globals_in_packages(symdb.get_package(view.file_name()), prefix)
        log('Из глобала', "%.3f" % (time.time() - t))
        return completions

    def get_completions_always(self, view):
        collections = sublime.find_resources('RSBIDE*.sublime-completions')
        sel = view.sel()[0]
        for collection_file in collections:
            collection_res = sublime.decode_value(
                sublime.load_resource(collection_file)
            )
            if view.match_selector(sel.begin(), collection_res.get('scope', 'source.mac')):
                completions = collection_res.get('completions', [])
            else:
                continue
            descr = collection_res.get('descr', '\trsl')
            for completion in completions:
                if 'trigger' in completion:
                    yield (completion['trigger'] + descr, completion['contents'])
                else:
                    yield (completion + descr, completion)


class RebuildCacheCommand(sublime_plugin.WindowCommand):
    index_in_progress = False
    exclude_folders = []

    def run(self, action='update'):
        log('run')
        if action == 'cancel':
            self.__class__.index_in_progress = False
            return
        self.view = self.window.active_view()
        if action == 'update':
            rebuild = False
        elif action == 'rebuild':
            rebuild = True
        else:
            raise ValueError('action must be one of {"cancel", "update", '
                             '"rebuild"}')

        self.__class__.index_in_progress = True
        db = get_db(self.view.window())

        async_worker.schedule(self.async_process_files,
                              db,
                              self.view.window().folders(), rebuild)

    def is_enabled(self, action='update'):
        self.view = self.window.active_view()
        if action == 'cancel':
            return self.index_in_progress
        else:
            return not self.index_in_progress

    @classmethod
    def async_process_files(cls, databases, project_folders, rebuild):
        try:
            cls.async_process_files_inner(databases, project_folders, rebuild)
        finally:
            cls.index_in_progress = False

    @classmethod
    def all_files_in_folders(self, folder, base=None):
        base = base if base is not None else folder
        for test in self.exclude_folders:
            if re.search('(?i)' + test, folder) is not None:
                return
        for x in os.listdir(folder):
            current_path = os.path.join(folder, x)
            if (os.path.isfile(current_path)):
                if not is_file_index(current_path):
                    continue
                yield posix(current_path)
            elif (not x.startswith('.') and os.path.isdir(current_path)):
                yield from self.all_files_in_folders(current_path, base)

    @classmethod
    def async_process_files_inner(cls, databases, project_folders, rebuild):
        if rebuild:
            # Helper process should not reference files to be deleted.
            imp.reload(symdb)

            # Simply remove associated database files if build from scratch is
            # requested.
            for database in databases:
                try:
                    os.remove(os.path.expandvars(database))
                except OSError:
                    # Specified database file may not yet exist or is
                    # inaccessible.
                    pass
        t = time.time()
        if not update_settings():
            return
        cls.exclude_folders = Settings.proj_settings.get('EXCLUDE_FOLDERS', [])
        for dbi, database in enumerate(databases):
            symdb.begin_file_processing(dbi)
            for folder in project_folders:
                aLL_f = list(cls.all_files_in_folders(folder))
                lf = len(aLL_f)
                t1 = time.time()
                for it, path in enumerate(aLL_f):
                    if not cls.index_in_progress:
                        symdb.end_file_processing(dbi)
                        symdb.commit()
                        sublime.status_message('Indexing canceled')
                        return
                    symdb.process_file(dbi, path)
                    p = it * 100 / lf
                    sublime.status_message(' RSL index %03.2f %%' % p)
                    if it > 0 and it % 1000 == 0:
                        symdb.commit()
                    if it > 0 and it % 100 == 0:
                        log(it, 'of', lf, "%.3f" % (time.time() - t1))
                        t1 = time.time()

            symdb.end_file_processing(dbi)
            symdb.commit()
            sublime.status_message(' RSL index Done %.3f sec' % (time.time() - t))
        log('Parse_ALL', "%.3f" % (time.time() - t))
        imp.reload(symdb)


class LintThisViewCommand(sublime_plugin.WindowCommand):

    def run(self):
        view = self.window.active_view()
        if not is_RStyle_view(view):
            return
        lint = Linter(view, force=True)
        lint.start()

    def is_visible(self):
        view = self.window.active_view()
        return is_RStyle_view(view) and Settings.proj_settings.get("LINT", True)

    def description(self):
        return 'RSBIDE: Проверить по соглашениям'


class PrintTreeImportCommand(sublime_plugin.WindowCommand):
    def run(self):
        view = self.window.active_view()
        if not update_settings():
            return
        imports = symdb.query_imports(symdb.get_package(view.file_name()))
        tree = Tree()
        package = symdb.get_package(view.file_name(), True)
        tree.add_node(package)
        for node in imports:
            tree.add_node(node[0], node[1])
        v = self.window.new_file()
        tree.display(package, view=v)
        v.run_command('append', {'characters': "\n"})

    def is_visible(self):
        return is_RStyle_view(self.window.active_view())

    def description(self):
        return 'RSBIDE: Дерево импортов'


class StatusBarFunctionCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        view = self.view
        if not is_RStyle_view(view):
            return
        self.settings = Settings.proj_settings
        lint = Linter(view)
        region = view.sel()[0]
        mess_list = []
        MessStat = ''
        sep = ';'
        cur_class = extent_reg(view, region)
        cur_macro = extent_reg(view, region, 2)
        lint_regions = [(j, lint.get_text_lint(i)) for i in lint.all_lint_regions() for j in view.get_regions(i)]
        if len(lint_regions) > 0:
            MessStat = 'Есть замечания: %s всего' % (len(lint_regions))
            for x in lint_regions:
                if x[0].intersects(region):
                    mess_list += [x[1]]
            if len(mess_list) > 0:
                MessStat = sep.join(mess_list)
        elif self.settings.get("SHOW_CLASS_IN_STATUS", False):
            if cur_class:
                parent = [el for el in view.find_by_selector('entity.other.inherited-class.mac') if cur_class[0].contains(el)]
                param = [p for p in view.find_by_selector('variable.parameter.class.mac') if cur_class[0].contains(p)]
                sp = '(%s)' % (''.join([view.substr(i) for i in parent])) if len(parent) > 0 else ''
                MessStat = 'class %s %s (%s)' % (sp, view.substr(cur_class[1]), ', '.join([view.substr(j) for j in param]))
            if cur_macro:
                if len(MessStat) > 0:
                    MessStat += ','
                MessStat += ' macro: ' + view.substr(cur_macro[1])
        view.set_status('rsbide_stat', MessStat)


class RunRsinitCommand(sublime_plugin.TextCommand):

    currfolder = ""

    def run(self, edit, action='file'):
        def call_a():
            log(call(['RSInit.exe', '-rsldebug', symdb.get_package(self.view.file_name()) + '.mac']))
        if action != 'file':
            return
        os.chdir(self.currfolder)
        sublime.set_timeout_async(call_a, 5)

    def is_visible(self):
        return os.path.lexists(os.path.join(self.currfolder, 'RSInit.exe'))

    def is_enabled(self):
        self.currfolder = sublime.expand_variables(
            "$folder", sublime.active_window().extract_variables())
        if is_RStyle_view(self.view):
            return True
        else:
            return False

    def description(self):
        return 'RSBIDE: Запуск/Отладка файла'


def plugin_loaded():
    if not update_settings():
        return
    global_settings = sublime.load_settings(config["RSB_SETTINGS_FILE"])
    global_settings.clear_on_change('RSBIDE_settings')
    global_settings.add_on_change("RSBIDE_settings", update_settings)


def update_settings():
    """ restart projectFiles with new plugin and project settings """
    # update settings
    db = get_db(sublime.active_window())
    if len(db) == 0:
        debug('Не задана БД')
        return False
    symdb.set_databases(db)
    if Settings:
        global_settings = Settings.update()
        settings = Settings.merge(global_settings, Settings.project(sublime.active_window()))
        Settings.set_settings_project(settings)
        symdb.set_settings(Settings)
    return True
