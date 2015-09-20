# coding=cp1251
# ------------------------------------------------------------------------------
# RSBIDE Sublime Text Plugin
# forked from https://github.com/eladyarkoni/MySignaturePlugin
# 09.09.2015
# FOR RS BALANCE Programmed by MOM
# ------------------------------------------------------------------------------
import sublime
import sublime_plugin
import os
import pickle
import re
import threading
import codecs
import time
import xml.etree.ElementTree as ET
from os.path import basename, dirname, normpath, normcase, realpath
from RSBIDE.tree import Tree
from RSBIDE.RsbIde_print_panel import get_panel

try:
    import thread
except:
    import _thread as thread


global debug
debug = False
global already_im
already_im = []
obj = []
fields = []
methods = []


class RSBIDE:

    files = dict()
    filesxml = dict()
    filesimport = dict()
    ffiles = []

    NAME = 'name'
    SIGN = 'sign'
    COMPLETION = 'completion'

    EMPTY = ''
    tmp_folder = os.path.expandvars(r'%TEMP%')

    def clear(self):
        self.files = dict()
        self.filesxml = dict()
        self.filesimport = dict()
        self.ffiles = []

    def rebuild_cache(self):
        if not Pref.scan_running:
            self.clear()
            RSBIDECollectorThread().start()

    def save_functions(self, file, data):
        self.files[file] = data

    def save_objs(self, stype, data):
        self.filesxml[stype] = data

    def save_imports(self, file, data):
        self.filesimport[file] = data

    def save_ff(self, file):
        lfile = normalize_to_system_style_path(file.lower())
        file  = normalize_to_system_style_path(file)
        if file in self.ffiles:
            return
        for x in self.ffiles:
          if lfile == x.lower():
                self.ffiles.remove(x)
        self.ffiles.append(file)

    def save_to_cache(self):
        if os.path.lexists(self.tmp_folder):
            with open(os.path.join(self.tmp_folder, 'files_cache.obj'), 'wb') as cache_file:
                pickle.dump(self.files, cache_file)
            with open(os.path.join(self.tmp_folder, 'filesxml_cache.obj'), 'wb') as cache_file:
                pickle.dump(self.filesxml, cache_file)
            with open(os.path.join(self.tmp_folder, 'filesimport_cache.obj'), 'wb') as cache_file:
                pickle.dump(self.filesimport, cache_file)
            with open(os.path.join(self.tmp_folder, 'ffiles_cache.obj'), 'wb') as cache_file:
                pickle.dump(self.ffiles, cache_file)


    def load_from_cache(self):
        if os.path.lexists(os.path.join(self.tmp_folder, 'files_cache.obj')):
            with open(os.path.join(self.tmp_folder, 'files_cache.obj'), 'rb') as cache_file:
                    try:
                        self.files = pickle.load(cache_file)
                    except Exception:
                        os.remove(cache_file)
                        self.files = dict()
        if os.path.lexists(os.path.join(self.tmp_folder, 'filesxml_cache.obj')):
            with open(os.path.join(self.tmp_folder, 'filesxml_cache.obj'), 'rb') as cache_file:
                    try:
                        self.filesxml = pickle.load(cache_file)
                    except Exception:
                        os.remove(cache_file)
                        self.filesxml = dict()
        if os.path.lexists(os.path.join(self.tmp_folder, 'filesimport_cache.obj')):
            with open(os.path.join(self.tmp_folder, 'filesimport_cache.obj'), 'rb') as cache_file:
                    try:
                         self.filesimport = pickle.load(cache_file)
                    except Exception:
                         os.remove(cache_file)
                         self.filesimport = dict()
        if os.path.lexists(os.path.join(self.tmp_folder, 'ffiles_cache.obj')):
            with open(os.path.join(self.tmp_folder, 'ffiles_cache.obj'), 'rb') as cache_file:
                    try:
                         self.ffiles = pickle.load(cache_file)
                    except Exception:
                         os.remove(cache_file)
                         self.ffiles = []

    def without_duplicates(self, words):
        result = []
        used_words = []
        for w, v in words:
            if w.lower() not in used_words:
                used_words.append(w.lower())
                result.append((w, v))
        return result

    def get_completions(self, view, prefix):
        skip_deleted = Pref.forget_deleted_files
        # completion import files
        if view.scope_name(view.sel()[0].a) == "source.mac import.file.mac ":
            currentImport = [os.path.splitext(basename(view.substr(s).lower().strip()))[0] for s in view.find_by_selector('import.file.mac')]
            pfiles = self.ffiles
            lfile = [self.create_var_completion(os.path.splitext(basename(fil))[0],"File") for fil in pfiles if os.path.splitext(basename(fil.lower()))[0] not in currentImport]
            lfile = self.without_duplicates(list(lfile))
            lfile.sort()
            return lfile
        # start with default completions
        completions = list(Pref.always_on_auto_completions)
        # word completion from xml
        for stype, word in self.filesxml.items():
            for x in word:
                completions.append(self.create_var_completion(x, stype))
        self.get_files_import(view.file_name(), True)
        # append these from indexed files
        already_in = []
        for file, data in self.files.items():
            if basename(file).lower() not in already_im or norm_path_string(
                sublime.expand_variables("$folder", sublime.active_window().extract_variables())) not in file.lower():
                continue
            if not skip_deleted or (skip_deleted and os.path.lexists(file)):
                location = basename(file)
                for function in data:
                    if prefix.lower() in function[self.NAME].lower():
                        already_in.append(function[self.NAME])
                        completion = self.create_function_completion(
                            function, location)
                        completions.append(completion)
        # current file
        location = basename(view.file_name()) if view.file_name() else ''
        if debug:
            print (view.file_name())
        # append functions from current view that yet have not been saved
        [completions.append(self.create_function_completion(self.parse_line(view.substr(view.line(selection))), location)) for selection in view.find_by_selector('entity.name.function') if view.substr(selection) not in already_in and (already_in.append(view.substr(selection)) or True)]

        # append "var" names from current file
        vars = []
        [view.substr(selection) for selection in view.find_all('([var\s+]|\.|\()(\w+)\s*[=|:]', 0, '$2', vars)]
        [completions.append(self.create_var_completion(var, location)) for var in list(set(vars)) if len(var) > 1 and var not in already_in and (already_in.append(var) or True)]
        # append "globals from CommonVariables.mac"
        [completions.append(self.create_var_completion(var, "Global")) for var in list(set(self.get_globals(view))) if len(var) > 1 and var not in already_in]
        completions = self.without_duplicates(completions)
        return completions

    def create_function_completion(self, function, location):
        if self.COMPLETION not in function:
            name = function[self.NAME] + '(' + function[self.SIGN] + ')'
            if function[self.SIGN].strip() == self.EMPTY:
                hint = self.EMPTY
            else:
                hint = ", ".join(["${%s:%s}" % (k+1, v.strip()) for k, v in enumerate(function[self.SIGN].split(','))])
            function[self.COMPLETION] = (name + '\t' + location, function[self.NAME] + '(' + hint+')')
            del function[self.SIGN]  # no longer needed
        return function[self.COMPLETION]

    def create_var_completion(self, var, location):
        return (var + '\t' + location, var)

    def parse_line(self, line):
        for regexp in Pref.expressions:
            matches = regexp(line)
            if matches:
                return matches.groupdict()

    def get_globals(self, view):
        gvars = []
        if view == None:
            return gvars
        pfile = [sfile for sfile in self.files if basename(sfile).lower() == "CommonVariables.mac".lower()][0]
        lines = [line.rstrip('\r\n') + "\n" for line in codecs.open(pfile, encoding='cp1251', errors='replace') if len(line) < 300]
        parse_panel = get_panel(view, "".join(lines))
        gvars = [parse_panel.substr(parse_panel.word(selection)) for selection in parse_panel.find_by_selector('variable.declare.name.mac')]
        return gvars

    def parseimport(self, total):
         sregexp2 = r'(\"?((([\w\d])*)(?:.mac)*)\"?)\s*(?:(,|;))'
         imstrip = re.compile(re.escape('import '), re.IGNORECASE)
         return [imstrip.sub('', x[2].strip("\r\n")) for x in re.findall(sregexp2, total, re.I)]

    def get_files_import(self, file, isReset):
        global already_im
        if isReset:
            already_im = []
        t = time.time()
        LInFile = []
        bfile = basename(norm_path_string(file))
        if bfile.lower() not in [x.lower() for x in already_im]:
                LInFile.append(bfile)
                already_im.append(bfile)
        for file_im in LInFile:
            if file_im not in self.filesimport.keys():
                continue
            difflist = list(set(self.filesimport[file_im]) - set([x.lower() for x in already_im]))
            already_im.extend(difflist)
            currdiff = list(set(self.filesimport[file_im]) - set([x.lower() for x in LInFile]))
            LInFile.extend(currdiff)
        if debug:
            print('Scan import done in '+str(time.time()-t)+' seconds')


RSBIDE = RSBIDE()


class RSBIDEImportCollectorThread(threading.Thread):

    def __init__(self, file=None):
        self.file = file
        threading.Thread.__init__(self)

    def run(self):
        if self.file:
            try:
                RSBIDE.get_files_import(norm_path(self.file), True)
            except:
                pass


class RSBIDECollectorThread(threading.Thread):
    # the thread will parse or reparse a file if the file argument is present
    # if the "file" argument is not present, then will rescan the folders
    def __init__(self, file=None):
        self.file = file
        threading.Thread.__init__(self)

    def run(self):
        if self.file:
            try:
                self.parse_functions(norm_path(self.file))
                RSBIDE.filesimport[norm_path(self.file)] = []
                self.parse_import(norm_path(self.file))
                RSBIDE.save_ff(self.file)
                RSBIDE.save_to_cache()
            except:
                pass
        elif not Pref.scan_running:
            sublime.status_message('Scaning Run')
            Pref.scan_running = True
            Pref.scan_started = time.time()
            # the list of opened files in all the windows
            files = list(Pref.updated_files)
            # the list of opened folders in all the windows
            folders = list(Pref.updated_folders)
            Pref.folders = list(folders)
            # add also as folders, the dirname of the current opened files
            folders += [norm_path(dirname(file)) for file in files]
            # deduplicate
            folders = list(set(folders))
            _folders = []
            for folder in folders:
                _folders = deduplicate_crawl_folders(_folders, folder)
            folders = _folders

            if debug:
                print('Folders to scan:')
                print("\n".join(folders))

            # pasing
            files_seen = 0
            files_mac = 0
            files_xml = 0
            files_cache_miss = 0
            files_cache_miss_xml = 0
            files_cache_hit = 0
            files_cache_hit_xml = 0
            files_failed_parsing = 0
            files_failed_parsing_xml = 0

            # parse files with priority
            for file in files:
                if should_abort():
                    break
                files_seen += 1
                files_mac += 1
                if file not in RSBIDE.files:
                    try:
                        self.parse_functions(file)
                        self.parse_import(file)
                        files_cache_miss += 1
                    except:
                        files_failed_parsing += 1
                else:
                    files_cache_hit += 1

            # now parse folders
            for folder in folders:
                if should_abort():
                    break
                for dir, dnames, files in os.walk(folder):
                    if should_abort():
                        break
                    for f in files:
                        if should_abort():
                            break
                        files_seen += 1
                        file = os.path.join(dir, f)
                        if not should_exclude(file.lower()) and is_mac_file(file.lower()):
                            files_mac += 1
                            RSBIDE.save_ff(file)
                            file = norm_path(file)
                            if file not in RSBIDE.files:
                                try:
                                    self.parse_functions(file)
                                    self.parse_import(file)
                                    files_cache_miss += 1
                                except:
                                    files_failed_parsing += 1
                            else:
                                files_cache_hit += 1
                        elif not should_exclude(file.lower()) and is_xml_file(file.lower()):
                            files_xml += 1
                            file = norm_path(file)
                            if file not in RSBIDE.filesxml:
                                try:
                                    self.parse_xml(file)
                                    files_cache_miss_xml += 1
                                except:
                                    files_failed_parsing_xml += 1
                            else:
                                files_cache_hit_xml += 1
            obj.sort()
            fields.sort()
            methods.sort()
            RSBIDE.save_objs("Object", obj)
            RSBIDE.save_objs("Field", fields)
            RSBIDE.save_objs("Method", methods)
            RSBIDE.save_to_cache()
            sublime.status_message('Scan done in ' + str(time.time()-Pref.scan_started) + ' seconds - ' + 'File scans ' + str(files_mac + files_xml))
            if debug:
                print('Scan done in '+str(time.time()-Pref.scan_started)+' seconds - Scan was aborted: '+str(Pref.scan_aborted))
                print('Files Seen:'+str(files_seen)+', Files MAC:'+str(files_mac)+', Cache Miss:'+str(files_cache_miss)+', Cache Hit:'+str(files_cache_hit)+', Failed Parsing:'+str(files_failed_parsing))
                print('Files Seen:'+str(files_seen)+', Files XML:'+str(files_xml)+', Cache Miss:'+str(files_cache_miss_xml)+', Cache Hit:'+str(files_cache_hit_xml)+', Failed Parsing:'+str(files_failed_parsing))

            Pref.scan_running = False
            Pref.scan_aborted = False

    def parse_functions(self, file):
        if debug:
            print('\nParsing functions for file:\n'+file)
        pattern = re.compile(r"^\s*(macro)\s+", re.I | re.S)
        lines = [line.rstrip('\r\n') + "\n" for line in codecs.open(file, encoding='cp1251', errors='replace') if len(line) < 300 and pattern.match(line.lower())]
        functions = []
        for line in lines:
            matches = RSBIDE.parse_line(line)
            if matches and matches not in functions:
                functions.append(matches)
        RSBIDE.save_functions(file, functions)

    def parse_import(self, file):
        if debug:
            print('\nParsing import in file:\n'+file)
        pattern = re.compile(r"^\s*(import)\s+", re.I | re.S)
        lines = [line for line in codecs.open(file, encoding='cp1251', errors='replace') if len(line) < 300 and pattern.match(line.lower())]
        matches = RSBIDE.parseimport("".join(lines))
        imporFiles = list(set([mort.strip() + ".mac" for mort in [it.lower() for it in matches]]))
        RSBIDE.save_imports(basename(file), imporFiles)

    def get_name(self, elem, lelem=None):
        for i in elem:
            sname = i.get('Name')
            if sname not in lelem:
                lelem.append(sname)

    def parse_xml(self, file):
        lines = [line for line in codecs.open(file, encoding='cp1251', errors='replace')]
        root = ET.fromstring("".join(lines))
        self.get_name(root.findall("./object"), obj)
        self.get_name(root.findall("./object/Field"), fields)
        self.get_name(root.findall("./object/Method"), methods)


class RSBIDEEventListener(sublime_plugin.EventListener):

    def on_post_save(self, view):
        if is_RStyle_view(view):
            RSBIDECollectorThread(view.file_name()).start()

    def on_load(self, view):
        if is_RStyle_view(view) and is_mac_file(view.file_name()):
            if norm_path(view.file_name()) not in RSBIDE.files:
                RSBIDECollectorThread(view.file_name()).start()

    def on_activated_async(self, view):
        update_folders()
        if is_mac_file(view.file_name()):
            RSBIDEImportCollectorThread(view.file_name()).start()

    def on_query_completions(self, view, prefix, locations):
        if is_RStyle_view(view, locations):
            return (RSBIDE.get_completions(view, prefix), 0)
        return ([], 0)

global Pref, s

Pref = {}
s = {}


def is_RStyle_view(view, locations=None):
    return (view.file_name() and is_mac_file(view.file_name())) or ('RStyle' in view.settings().get('syntax')) or (locations and len(locations) and '.mac' in view.scope_name(locations[0]))


def is_mac_file(file):
    return file and file.endswith('.mac') and '.min.' not in file


def is_xml_file(file):
    return file and file.endswith('.xml') and '.min.' not in file


def norm_path(file):
    return normcase(normpath(realpath(file))).replace('\\', '/')


def norm_path_string(file):
    return file.strip().lower().replace('\\', '/').replace('//', '/')


def normalize_to_system_style_path(path):
    if sublime.platform() == 'windows':
        path= re.sub(r"/([A-Za-z])/(.+)", r"\1:/\2", path)
        path= re.sub(r"/", r"\\", path)
    return path


def should_exclude(file):
    return len([1 for exclusion in Pref.excluded_files_or_folders if exclusion in norm_path_string(file).split('/')])


def update_folders():
    folders = list(set([norm_path(folder) for w in sublime.windows() for folder in w.folders() if folder and not should_exclude(norm_path(folder))]))
    _folders = []
    for folder in folders:
        _folders = deduplicate_crawl_folders(_folders, folder)
    _folders.sort()
    Pref.updated_folders = _folders
    Pref.updated_files = [norm_path(v.file_name()) for w in sublime.windows() for v in w.views() if v.file_name() and is_mac_file(v.file_name()) and not should_exclude(norm_path(v.file_name()))]


def should_abort():
    if time.time() - Pref.scan_started > Pref.scan_timeout:
        Pref.scan_aborted = True
    return Pref.scan_aborted


def deduplicate_crawl_folders(items, item):
    # returns folders without child subfolders
    new_list = []
    add = True
    for i in items:
        if i.find(item+'\\') == 0 or i.find(item+'/') == 0:
            continue
        else:
            new_list.append(i)
        if (item+'\\').find(i+'\\') == 0 or (item+'/').find(i+'/') == 0:
            add = False
    if add:
        new_list.append(item)
    return new_list


class Pref():

    def load(self):
        if debug:
            print('-----------------')
        Pref.excluded_files_or_folders = [norm_path_string(file) for file in s.get('excluded_files_or_folders', [])]
        if debug:
            print('excluded_files_or_folders')
            print(Pref.excluded_files_or_folders)

        Pref.forget_deleted_files = s.get('forget_deleted_files', False)

        Pref.expressions = [re.compile(v, re.I).search for v in [
            r'macro\s*(?P<name>\w+)\s*\((?P<sign>[^\)]*)(\)|\n)',
            r'macro\s*(?P<name>\w+)\s*(?P<sign>)'
        ]]
        Pref.folders = []

        Pref.always_on_auto_completions = [(re.sub('\${[^}]+}', 'aSome', w), w) for w in s.get('always_on_auto_completions', [])]

        Pref.scan_running = False  # to avoid multiple scans at the same time
        Pref.scan_aborted = False  # for debuging purposes
        Pref.scan_started = 0
        Pref.scan_timeout = 60  # seconds

        update_folders()

        RSBIDE.load_from_cache()
        RSBIDECollectorThread().start()

class RebuildCacheCommand(sublime_plugin.WindowCommand):
    def run(self):
        RSBIDE.rebuild_cache()

class PrintSignToPanelCommand(sublime_plugin.WindowCommand):
    """Show declare func in panel"""
    def run(self):
        ST3 = int(sublime.version()) > 3000
        if ST3:
            from RSBIDE.RsbIde_print_panel import print_to_panel
        view = self.window.active_view()
        sel = view.sel()[0]
        if sel.begin() == sel.end():
            sel = view.expand_by_class(
                sel, sublime.CLASS_WORD_START | sublime.CLASS_WORD_END)
        symbol = get_result(view)
        if len(symbol) == 0:
            print_to_panel(view, view.substr(sel) + " not found in index")
            return
        file = normalize_to_system_style_path(symbol[0][0])
        nline = symbol[0][2][0]
        lnline = 0
        lines = []
        for i, line in enumerate(codecs.open(file, encoding='cp1251', errors='replace')):
            if i >= nline-10 and i <= nline + 9:
              lines.append(line.rstrip('\r\n'))
            if nline == i:
                lnline = len(lines)
        print_to_panel(view, "\n".join(lines), showline=lnline)

def getShortPathName(path):
    import ctypes
    from ctypes.wintypes import MAX_PATH
    buf = ctypes.create_unicode_buffer(MAX_PATH)
    GetShortPathName = ctypes.windll.kernel32.GetShortPathNameW
    rv = GetShortPathName(path, buf, MAX_PATH)
    if rv == 0 or rv > MAX_PATH:
        return path
    else:
        return buf.value

def getLongPathName(path):
    import ctypes
    from ctypes.wintypes import MAX_PATH
    buf = ctypes.create_unicode_buffer(MAX_PATH)
    GetLongPathName = ctypes.windll.kernel32.GetLongPathNameW
    rv = GetLongPathName(path, buf, MAX_PATH)
    if rv == 0 or rv > MAX_PATH:
        return path
    else:
        return buf.value

def _get_case_sensitive_name(s):
        """ Returns long name in case sensitive format """
        path = getLongPathName(getShortPathName(s))
        return path

def get_result(view):
    sel = view.sel()[0]
    window = sublime.active_window()
    if sel.begin() == sel.end():
        sel = view.expand_by_class(
            sel, sublime.CLASS_WORD_START | sublime.CLASS_WORD_END)

    word = view.substr(sel)
    if view.scope_name(view.sel()[0].a) == "source.mac import.file.mac ":
        res = []
        for file in RSBIDE.ffiles:
            if basename(file).lower() ==  word.lower() + ".mac":
                file = _get_case_sensitive_name(normalize_to_system_style_path(file))
                file = "/"+file.replace(":","").replace('\\', '/')
                sfile = file
                for x in Pref.updated_folders:
                    sfile = sfile.replace("/"+_get_case_sensitive_name(normalize_to_system_style_path(x)).replace(":","").replace('\\','/')+"/","")
                res.append((file, sfile, (0,0)))
        return res
    else:
        for file, data in RSBIDE.files.items():
            if basename(file).lower() not in list(map(str.lower, already_im)):
                continue
            for func in data:
                if func[RSBIDE.NAME].lower() == word.lower():
                    word = func[RSBIDE.NAME]
                    break

    result = window.lookup_symbol_in_index(word)
    im_result = []
    if len(result) > 1:
        for item in result:
            if basename(norm_path_string(item[0])) in already_im:
                 im_result.insert(already_im.index(basename(norm_path_string(item[0]))), item)
        result = im_result
    # elif len(result) == 0:
    #     vars = []
    #     [view.substr(selection) for selection in view.find_all('([var\s+]|\.|\()(\w+)\s*[=|:]', 0, '$2', vars)]
    #     result[0] = view.file_name() if view.file_name() else ''
    #     result[0][1] = basename(result[0])
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
            sublime.status_message("Symbol not found in index")
            # Здесь можно добавить переход на объяву переменных
            # Сложность в том что
            # переменные с одинаковым названием могут быть объявлены
            # несколько раз (в каждой функции) и не понятно к какой переходить
            # print(view.file_name())
            # self.open_file(0)
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


class PrintTreeImportCommand(sublime_plugin.WindowCommand):
   def run(self):
        view = self.window.active_view()
        (_ROOT, _DEPTH, _BREADTH) = range(3)
        LInFile = []
        tree = Tree()
        bfile = basename(norm_path_string(view.file_name()))
        LInFile.append(bfile)
        tree.add_node(bfile)  # root node

        for file_im in LInFile:
            # print("Analiz file: ", file_im)
            if file_im not in RSBIDE.filesimport.keys():
                continue
            # print("In Cashe: \n", list(set(RSBIDE.filesimport[file_im])))
            # print("In Tree: ")
            for i in list(set(RSBIDE.filesimport[file_im])):
                if i not in tree[file_im].children:
                    if i not in LInFile:
                        LInFile.append(i)
                        tree.add_node(i, file_im)
                    else:
                        tree.add_node(i+"_"+str(len(LInFile)), file_im)
        tree.display(bfile, pathfile=norm_path_string(view.file_name())+".treeimport")
        self.window.open_file("%s:%s:%s" % (view.file_name()+".treeimport", 0, 0), sublime.ENCODED_POSITION)


def RSBIDE_folder_change_watcher():
    while True:
        time.sleep(5)
        if not Pref.scan_running and Pref.updated_folders != Pref.folders:
            RSBIDECollectorThread().start()


def plugin_loaded():
    global Pref, s
    s = sublime.load_settings('RSBIDE.sublime-settings')
    Pref = Pref()
    Pref.load()
    s.clear_on_change('reload')
    s.add_on_change('reload', lambda: Pref.load())

    if not 'running_RSBIDE_folder_change_watcher' in globals():
        running_RSBIDE_folder_change_watcher = True
        thread.start_new_thread(RSBIDE_folder_change_watcher, ())

if int(sublime.version()) < 3000:
    sublime.set_timeout(lambda: plugin_loaded(), 0)
