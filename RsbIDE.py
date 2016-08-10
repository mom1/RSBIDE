# -*- coding: cp1251 -*-
# @Author: MOM
# @Date:   2015-09-09 21:44:10
# @Last Modified by:   mom1
# @Last Modified time: 2016-08-10 20:03:51


import sublime
import sublime_plugin
import os
import json
import re
import codecs
import time
import xml.etree.ElementTree as ET
from os.path import basename, dirname, normpath, normcase, realpath
from RSBIDE.tree import Tree
from RSBIDE.RsbIde_print_panel import get_panel

from RSBIDE.common.verbose import verbose, log
from RSBIDE.project.ProjectManager import ProjectManager
import RSBIDE.common.parser as parser
from RSBIDE.project.Project import Project
import RSBIDE.common.settings as Settings
from RSBIDE.common.config import config
import RSBIDE.common.path as Path
from RSBIDE.project.CurrentFile import CurrentFile
import RSBIDE.common.lint as Linter


global IS_ST3
IS_ST3 = sublime.version().startswith('3')


global already_im
already_im = []
ID = 'RSBIDE'
scope_cache = {}


class RSBIDE:

    def rebuild_cache(self):
        project = ProjectManager.get_current_project()
        os.remove(os.path.join(os.path.expandvars(r'%TEMP%'), project.filecache.cache.files_cache))
        project.rebuild_filecache()

    def without_duplicates(self, words):
        result = []
        used_words = []
        for w, v in words:
            if w.lower() not in used_words:
                used_words.append(w.lower())
                result.append((w, v))
        return result

    def get_from_metadata(self, view):
        project = ProjectManager.get_current_project()
        return project.get_all_list_metadate()

    def get_completions(self, view, prefix):
        # completion from cache
        completions = []
        t = time.time()
        t1 = time.time()
        verbose(ID, view.scope_name(view.sel()[0].a))
        scope = view.scope_name(view.sel()[0].a)
        if "source.mac meta.import.mac" in scope or 'punctuation.definition.import.mac' in scope:
            # completion for import
            currentImport = [os.path.splitext(basename(
                view.substr(s).lower().strip()))[0] for s in view.find_by_selector('meta.import.mac import.file.mac')]
            project = ProjectManager.get_current_project()
            pfiles = project.filecache.cache.files
            lfile = [self.create_var_completion(os.path.splitext(
                basename(fil))[0], "File") for fil in pfiles if os.path.splitext(
                    basename(fil.lower()))[0] not in currentImport]
            lfile = self.without_duplicates(list(lfile))
            lfile.sort()
            return lfile
        sel = view.sel()[0]
        if "string.quoted.double" in scope:
            completions += self.get_from_metadata(view)
        log(ID, 'Из метаданных ' + str(time.time() - t) + ' sec')
        t = time.time()
        if sel.begin() == sel.end():
            sel = view.word(sel)

        project = ProjectManager.get_current_project()
        project_folder = project.get_directory()
        # current file completion
        classRegs = [clreg for clreg in view.find_by_selector('meta.class.mac') if clreg.contains(sel)]
        macroRegs = [mcreg for mcreg in view.find_by_selector('meta.macro.mac') if mcreg.contains(sel)]
        sclass = 'meta.class.mac entity.name.class.mac'
        smacro = 'meta.macro.mac entity.name.function.mac'
        svaria = 'variable.declare.name.mac'
        sismacro = ''
        sparammacro = ''
        sparamclass = ''
        if len(classRegs) == 0:
            smacro += ' - meta.class.mac'
            svaria += ' - meta.class.mac'
        else:
            sparamclass += ', variable.parameter.class.mac'
        if len(macroRegs) == 0:
            sismacro += ' - meta.macro.mac'
        else:
            sparammacro += ', variable.parameter.macro.mac%s' % (sismacro)
            sparamclass = ''

        svaria = 'variable.declare.name.mac%s%s%s' % (sismacro, sparammacro, sparamclass)

        result = []
        filename, extension = os.path.splitext((view.file_name()))
        regions = [i for i in view.find_by_selector(sclass + ', ' + smacro + ', ' + svaria)]

        if len(classRegs) > 0:
            regions = [i for i in regions if classRegs[0].contains(i)]
        for x in regions:
            if 'entity.name.function.mac' in view.scope_name(x.a):
                region = [i for i in view.find_by_selector('meta.macro.mac') if i.contains(x)]
                name_param = [view.substr(i) for i in view.find_by_selector('variable.parameter.macro.mac') if region[0].contains(i)]
                hint = ", ".join(["${%s:%s}" % (k + 1, v.strip()) for k, v in enumerate(name_param)])
                result.append((view.substr(x) + '(...)\t' + 'macro', view.substr(x) + '(' + hint + ')'))
            elif'variable.parameter.macro.mac' in view.scope_name(x.a):
                if macroRegs[0].contains(x):
                    result.append((view.substr(x) + '\t' + 'macro param', view.substr(x)))
            elif'variable.declare.name.mac' in view.scope_name(x.a):
                    c = 0
                    if len(macroRegs) > 0:
                        if macroRegs[0].contains(x):
                            result.append((view.substr(x) + '\t' + 'var in macro', view.substr(x)))
                            c += 1
                    if len(classRegs) > 0 and c == 0 and 'meta.macro.mac' not in view.scope_name(x.a):
                        if classRegs[0].contains(x):
                            result.append((view.substr(x) + '\t' + 'var in class', view.substr(x)))
                            c += 1
                    if c == 0 and ('meta.macro.mac' not in view.scope_name(x.a) or 'meta.class.mac' not in view.scope_name(x.a)):
                        result.append((view.substr(x) + '\t' + 'global', view.substr(x)))
            else:
                result.append((view.substr(x) + '\t' + 'current file', view.substr(x)))
        completions += result
        log(ID, 'Текущ. файл ' + str(time.time() - t) + ' sec')
        t = time.time()
        # from parent comletion
        # completions += get_declare_in_parent(view, classRegs, None)
        regions_parent = [i for i in view.find_by_selector('entity.other.inherited-class.mac') for j in classRegs if j.contains(i)]
        if len(regions_parent) == 0:
            class_word = None
        else:
            class_word = view.substr(regions_parent[0])
        completions += parser.get_parent_completion(class_word, project)
        log(ID, 'Из родителя ' + str(time.time() - t) + ' sec')
        t = time.time()
        completions += parser.get_globals_completion(get_imports(view.file_name()), project)
        log(ID, 'Из глобала ' + str(time.time() - t) + ' sec')
        # t = time.time()

        completions = self.without_duplicates(completions)
        log(ID, 'Дубли ' + str(time.time() - t) + ' sec')
        t = time.time()

        # start with default completions
        # completions = list(Pref.always_on_auto_completions)
        log(ID, 'Автокомплит ' + str(time.time() - t1) + ' sec')
        return completions


RSBIDE = RSBIDE()


def is_RStyle_view(view, locations=None):
    return (
        view.file_name() and is_mac_file(view.file_name()) or
        ('RStyle' in view.settings().get('syntax')) or ('R-Style' in view.settings().get('syntax')) or
        (locations and len(locations) and '.mac' in view.scope_name(locations[0])))


def is_mac_file(file):
    return file and file.endswith('.mac') and '.min.' not in file


def norm_path(file):
    return normcase(normpath(realpath(file))).replace('\\', '/')


def norm_path_string(file):
    return file.strip().lower().replace('\\', '/').replace('//', '/')


def normalize_to_system_style_path(path):
    if sublime.platform() == 'windows':
        path = re.sub(r"/([A-Za-z])/(.+)", r"\1:/\2", path)
        path = re.sub(r"/", r"\\", path)
    return path


class RebuildCacheCommand(sublime_plugin.WindowCommand):

    def run(self):
        RSBIDE.rebuild_cache()


class PrintSignToPanelCommand(sublime_plugin.WindowCommand):

    """Show declare func in panel"""

    cache = {}

    def run(self):
        global IS_ST3
        if IS_ST3:
            from RSBIDE.RsbIde_print_panel import print_to_panel
        view = self.window.active_view()
        sel = view.sel()[0]
        if sel.begin() == sel.end():
            sel = view.word(sel)
        symbol = get_result(view)
        if len(symbol) == 0:
            doc_string = self.get_doc(view)
            if doc_string:
                print_to_panel(view, doc_string, bDoc=True)
                return
            print_to_panel(view, view.substr(sel) + " not found in index")
            return
        file = normalize_to_system_style_path(symbol[0][0])
        nline = symbol[0][2][0]
        lnline = 0
        lines = []
        for i, line in enumerate(codecs.open(file, encoding='cp1251', errors='replace')):
            if i >= nline - 10 and i <= nline + 9:
                lines.append(line.rstrip('\r\n'))
            if nline == i:
                lnline = len(lines)
        print_to_panel(view, "\n".join(lines), showline=lnline, region_mark=symbol[0][2])

    def get_doc(self, view):
        lang = 'mac'
        path_db = os.path.dirname(
            os.path.abspath(__file__)) + "/dbHelp/%s.json" % lang

        if os.path.exists(path_db):
            self.cache[lang] = json.load(open(path_db))
        else:
            self.cache[lang] = {}

        words = [view.substr(view.word(view.sel()[0]))]
        completions = self.cache[lang]
        found = False
        for word in words:
            completion = completions.get(word.lower())
            if completion:
                found = completion
                break
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

    def is_visible(self, paths=None):
        view = self.window.active_view()
        return ('R-Style' in view.settings().get('syntax'))

    def description(self):
        return 'RSBIDE: Показать область объявления\talt+s'


def get_declare_in_parent(view, classRegs, sel):
    window = sublime.active_window()
    select = []
    pref = 'RSBIDE:Parse_'  # Префикс для панели парсинга
    project = ProjectManager.get_current_project()
    project_folder = project.get_directory()
    regions_parent = [i for i in view.find_by_selector('entity.other.inherited-class.mac') for j in classRegs if j.contains(i)]
    if len(regions_parent) == 0:
        return []
    else:
        region_parent = regions_parent[0]
    word = view.substr(region_parent)
    result = window.lookup_symbol_in_index(word)
    for item in result:
        t = time.time()
        file = Path.posix(Path.get_absolute_path(project_folder, item[1]))
        filename, extension = os.path.splitext((file))
        lines = [line.rstrip('\r\n') + "\n" for line in codecs.open(file, encoding='cp1251', errors='replace')]
        parse_panel = get_panel(sublime.active_window().active_view(), "".join(lines), name_panel=pref + item[1])
        position = parse_panel.text_point(item[2][0] - 1, item[2][1])
        regions_class = [i for i in parse_panel.find_by_selector('meta.class.mac') if i.contains(position)]
        log('Подготовка:', basename(filename), str(time.time() - t))
        if len(regions_class) == 0:
            continue
        region_class = regions_class[0]
        if sel is not None:
            select += [
                (item[0], item[1], (parse_panel.rowcol(i.a)[0] + 1, parse_panel.rowcol(i.a)[1] + 1))
                for i in parse_panel.find_by_selector('meta.class.mac variable.declare.name.mac - meta.macro.mac, meta.class.mac entity.name.function.mac')
                if region_class.contains(i) and sel.lower() == parse_panel.substr(i).lower()]
            if len(select) == 0:
                select += get_declare_in_parent(parse_panel, regions_class, sel)
        sublime.active_window().destroy_output_panel(pref + item[1])
    return select


def get_globals_in_import(view, word, fName):
    # global variable
    pref = 'RSBIDE:Parse_'  # Префикс для панели парсинга
    project = ProjectManager.get_current_project()
    project_folder = project.get_directory()
    select = []
    t = time.time()
    log('Не нашли в текущем ищем в импортах :' + fName, str(time.time() - t))
    t = time.time()
    already_im = get_imports(fName)
    log('Получили список импортов :', len(already_im), fName, str(time.time() - t))
    for rfile in already_im:
        file = Path.posix(Path.get_absolute_path(project_folder, rfile))
        filename, extension = os.path.splitext((file))
        lines = [line.rstrip('\r\n') + "\n" for line in codecs.open(file, encoding='cp1251', errors='replace')]
        parse_panel = get_panel(sublime.active_window().active_view(), "".join(lines), name_panel=pref + rfile)
        region_name = [
            i for i in parse_panel.find_by_selector(
                'variable.declare.name.mac - (meta.class.mac, meta.macro.mac), entity.name.function.mac - meta.class.mac, meta.class.mac entity.name.class.mac')
            if word.lower() == parse_panel.substr(i).lower()]
        for region in region_name:
            select += [(file, rfile, (parse_panel.rowcol(region.a)[0] + 1, parse_panel.rowcol(region.a)[1] + 1))]
        if len(select) > 0:
            break

        sublime.active_window().destroy_output_panel(pref + rfile)
    log('Конец обработки файла :' + fName, str(time.time() - t))
    return select


def get_imports(fName):
    # get all import file
    if "imports" in CurrentFile.current and len(CurrentFile.current["imports"]) != 0:
        log('Import from cache')
        already_im = CurrentFile.current["imports"]
    else:
        log('Import from file')
        project = ProjectManager.get_current_project()
        already_im = parser.get_import_tree(fName, project)
    return already_im


def get_result(view):
    sel = view.sel()[0]
    window = sublime.active_window()
    if sel.begin() == sel.end():
        sel = view.word(sel)

    project = ProjectManager.get_current_project()
    project_folder = project.get_directory()

    file = Path.posix(Path.get_absolute_path(project_folder, view.file_name()))
    sfile = Path.posix(os.path.relpath(file, project_folder))
    word = view.substr(sel)

    if word.lower() == 'end' and (
        'keyword.macro.end.mac' in view.scope_name(view.sel()[0].a) or
        'keyword.class.end.mac' in view.scope_name(view.sel()[0].a) or
        'keyword.if.end.mac' in view.scope_name(view.sel()[0].a) or
        'keyword.for.end.mac' in view.scope_name(view.sel()[0].a) or
        'keyword.while.end.mac' in view.scope_name(view.sel()[0].a)
    ):
        meta = view.extract_scope(sel.a - 1)
        row, col = view.rowcol(meta.a)
        return [(file, sfile, (row + 1, col + 1))]
        # log(view.substr())

    if view.scope_name(view.sel()[0].a) == "source.mac meta.import.mac import.file.mac ":  # if scope import go to file rowcol 0 0
        return [(val[3].get('fullpath'), i, (0, 0)) for i, val in project.find_file('/' + word.lower() + '.mac').items()]
    elif view.scope_name(view.sel()[0].a) == "source.mac meta.class.mac inherited-class.mac entity.other.inherited-class.mac ":
        return window.lookup_symbol_in_index(word)

    # result = window.lookup_symbol_in_index(word)
    result = []
    im_result = []
    classRegs = [clreg for clreg in view.find_by_selector('meta.class.mac') if clreg.contains(sel)]
    macroRegs = [mcreg for mcreg in view.find_by_selector('meta.macro.mac') if mcreg.contains(sel)]
    sclass = 'meta.class.mac entity.name.class.mac'
    smacro = 'meta.macro.mac entity.name.function.mac'
    svaria = 'variable.declare.name.mac'
    sismacro = ''
    sparammacro = ''
    sparamclass = ''
    if len(classRegs) == 0:
        smacro += ' - meta.class.mac'
        svaria += ' - meta.class.mac'
    else:
        sparamclass += ', variable.parameter.class.mac'
    if len(macroRegs) == 0:
        sismacro += ' - meta.macro.mac'
    else:
        sparammacro += ', variable.parameter.macro.mac%s' % (sismacro)
        sparamclass = ''

    svaria = 'variable.declare.name.mac%s%s%s' % (sismacro, sparammacro, sparamclass)

    vars = []
    selections = [i for i in view.find_by_selector(sclass + ', ' + smacro + ', ' + svaria) if word.lower() == view.substr(view.word(i)).lower()]
    RegionMacroParam = view.find_by_selector('variable.parameter.macro.mac')
    RegionClassParam = view.find_by_selector('variable.parameter.class.mac')

    if len(classRegs) > 0 and len(selections) > 1:
        # Ищем в текущем классе
        selections = [i for i in selections for j in classRegs if j.contains(i)]
    if len(macroRegs) > 0 and len(selections) > 1:
        # Нашли в текущем классе ищем  в текущем макро
        selections = [i for i in selections for j in macroRegs if j.contains(i)]
        for x in selections:
            if 'entity.name.function.mac' in view.scope_name(x.a):
                selections.remove(x)
    if len(macroRegs) > 0 and len(selections) == 0:
        # текущая позиция в макро но переменной в ней нет (ищем в параметрах текущего макро)
        MacroParamRegs = [i for i in RegionMacroParam if word.lower() == view.substr(view.word(i)).lower()]
        selections = [i for i in MacroParamRegs for j in macroRegs if j.contains(i)]
    elif len(macroRegs) == 0 and len(classRegs) > 0 and len(selections) == 0:
        # текущая позиция вне макро но в классе (ищем в параметрах класса)
        ClassParamRegion = [i for i in RegionClassParam if word.lower() == view.substr(view.word(i)).lower()]
        selections = [i for i in ClassParamRegion for j in classRegs if j.contains(i)]
    for selection in selections:
        # нашли в текущем классе, указываем где
        vars.append((file, sfile, (view.rowcol(selection.a)[0] + 1, view.rowcol(selection.a)[1] + 1)))
    if len(classRegs) > 0 and len(selections) == 0:
        # не нашли в текущем классе, ищем в родительских
        in_parent = get_declare_in_parent(view, classRegs, view.substr(sel))
        if len(in_parent) > 0:
            vars = in_parent
    if len(vars) == 0:
        # ни где не нашли, ищем в глобальных переменных
        var_globals = get_globals_in_import(view, word, sfile)
        if len(var_globals) > 0:
            vars = var_globals
    if len(vars) > 0:
        result = vars
    return result


class GoToDefinitionCommand(sublime_plugin.WindowCommand):
    def run(self):
        view = self.window.active_view()
        if not is_RStyle_view(view):
            return
        self.old_view = self.window.active_view()
        self.current_file_location = view.sel()[0].end()

        self.result = get_result(view)

        if len(self.result) == 1:
            self.open_file(0)
            return

        if len(self.result) == 0:
            sublime.status_message("RSBIDE: Symbol not found in index")
            return

        self.window.show_quick_panel(["%s (%s)" % (r[1], r[2][0]) for r in self.result], self.open_file, 0, 0, lambda x: self.open_file(x, True))

    def open_file(self, idx, transient=False):
            flags = sublime.ENCODED_POSITION

            if transient:
                flags |= sublime.TRANSIENT

            if idx > -1:
                self.window.open_file("%s:%s:%s" % (self.result[idx][0], self.result[idx][2][0], self.result[idx][2][1]), flags)
            else:
                self.window.focus_view(self.old_view)
                self.old_view.show_at_center(self.current_file_location)

    def is_visible(self, paths=None):
        view = self.window.active_view()
        return ('R-Style' in view.settings().get('syntax'))

    def description(self):
        return 'RSBIDE: Перейти к объявлению\talt+g'


class LintThisViewCommand(sublime_plugin.WindowCommand):
    def run(self):
        view = self.window.active_view()
        if not is_RStyle_view(view):
            return
        Linter.run_all_lint(view, ProjectManager)

    def is_visible(self):
        view = self.window.active_view()
        return ('R-Style' in view.settings().get('syntax'))

    def description(self):
        return 'RSBIDE: Проверить по соглашениям'


class PrintTreeImportCommand(sublime_plugin.WindowCommand):
    def run(self):
        view = self.window.active_view()
        project = ProjectManager.get_current_project()
        project_folder = project.get_directory()
        file = Path.posix(Path.get_absolute_path(project_folder, view.file_name()))
        sfile = Path.posix(os.path.relpath(file, project_folder))
        (_ROOT, _DEPTH, _BREADTH) = range(3)
        LInFile = []
        tree = Tree()
        bfile = basename(norm_path_string(view.file_name()))
        LInFile.append(sfile)
        tree.add_node(sfile)  # root node
        for file_im in LInFile:
            for x, val in project.find_file(file_im).items():
                for i in val[3].get('imports', []):
                    for rf in project.find_file('/' + i):
                        if not rf:
                            continue
                        if rf in LInFile:
                            continue
                        log('add ' + rf)
                        LInFile.append(rf)
                        tree.add_node(rf, file_im)
        log(len(LInFile))
        v = self.window.new_file()
        tree.display(sfile, view=v)
        v.run_command('append', {'characters': "\n"})


class StatusBarFunctionCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        view = self.view
        region = view.sel()[0]
        classRegs = [i for i in view.find_by_selector('meta.class.mac') if i.contains(region)]
        classRegsName = view.find_by_selector('meta.class.mac entity.name.class.mac')
        functionRegs = [n for n in view.find_by_selector('meta.macro.mac') if n.contains(region)]
        functionRegsName = view.find_by_selector('meta.macro.mac entity.name.function.mac')
        mess_list = []
        MessStat = ''
        sep = ';'
        lint_regions = [(i, Linter.get_text_lint('LongLines')) for i in view.get_regions('LongLines')]
        lint_regions += [(i, Linter.get_text_lint('comment_code')) for i in view.get_regions('comment_code')]
        lint_regions += [(i, Linter.get_text_lint('vare_unused')) for i in view.get_regions('vare_unused')]
        if len(lint_regions) > 0:
            MessStat = 'Есть замечания: %s всего' % (len(lint_regions))
            for x in lint_regions:
                if x[0].intersects(region):
                    mess_list += [x[1]]
            if len(mess_list) > 0:
                MessStat = sep.join(mess_list)
        else:
            for crn in [j for j in classRegsName for cr in classRegs if cr.contains(j)]:
                MessStat += ' Class: ' + view.substr(crn)
                break
            for mrn in [k for k in functionRegsName for mr in functionRegs if mr.contains(k)]:
                MessStat += ' Macro: ' + view.substr(mrn)
                break
        view.set_status('context', MessStat)


def plugin_loaded():
    update_settings()
    global_settings = sublime.load_settings(config["RSB_SETTINGS_FILE"])
    global_settings.add_on_change("update", update_settings)


def update_settings():
    """ restart projectFiles with new plugin and project settings """

    # invalidate cache
    global scope_cache
    scope_cache = {}
    # update settings
    global_settings = Settings.update()
    # update project settings
    ProjectManager.initialize(Project, global_settings)

if not IS_ST3:
    sublime.set_timeout(lambda: plugin_loaded(), 0)
