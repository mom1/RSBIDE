# -*- coding: utf-8 -*-
import os
import re
import time
import threading
import hashlib
import pickle
import codecs
from RSBIDE.RsbIde_print_panel import get_panel
import sublime
# import inspect
from RSBIDE.common.verbose import verbose
from RSBIDE.common.verbose import log
from RSBIDE.common.config import config
from RSBIDE.common.progress_bar import ProgressBar
import xml.etree.ElementTree as ET
from os.path import basename
"""
    Scans, parses and stores all files in the given folder to the dictionary `files`

    Each file entry is set by its relative `filepath` and holds an array like
        0 : filename (modified)
        1 : file extension
        2 : sublime text auto completion string
        3 : dict {
            fullname : fullpath file
            mtime    : date modification  time.ctime()
            imports  : file impors from this file
        }
"""
ID = "cache"


def posix(path):
    return path.replace("\\", "/")


class FileCacheWorker(threading.Thread):
    # stores all files and its fragments within property files

    def __init__(self, exclude_folders, extensions, folder):
        threading.Thread.__init__(self)

        self.exclude_folders = exclude_folders
        self.extensions = extensions
        self.folder = folder
        self.tmp_folder = os.path.expandvars(r'%TEMP%')
        self.m = hashlib.md5()
        self.m.update(self.folder.encode('utf-8'))
        self.files_cache = self.m.hexdigest() + '.' + ID
        self.last_add = []
        self.not_delete = []
        self.files = None
        self.meta_data = None
        self.load_from_cache()
        self.always_import = ['CommonVariables', 'CommonDefines', 'CommonClasses', 'CommonFunctions']

    def save_to_cache(self):
        if os.path.lexists(self.tmp_folder):
            with open(posix(os.path.join(self.tmp_folder, self.files_cache)), 'wb') as cache_file:
                pickle.dump((self.files, self.meta_data), cache_file)
            verbose(ID, 'cache save to ' + os.path.join(self.tmp_folder, self.files_cache))

    def load_from_cache(self):
        if os.path.lexists(os.path.join(self.tmp_folder, self.files_cache)):
            with open(posix(os.path.join(self.tmp_folder, self.files_cache)), 'rb') as cache_file:
                    try:
                        self.files, self.meta_data = pickle.load(cache_file)
                        verbose(ID, 'cache load from ' + os.path.join(self.tmp_folder, self.files_cache))
                    except Exception:
                        pass
                        os.remove(cache_file)
        else:
            self.files = {}
            self.meta_data = {}

    def parse_import(self, relative_path, fName, extension):
        pref = 'RSBIDE:Parse_import_'  # Префикс для панели парсинга
        if extension != 'mac':
            return [], []
        if not fName or not relative_path:
            verbose(ID, 'Нет файла для анализа')
            return [], []
        names_import = []
        names_global = []
        lines = [line.rstrip('\r\n') + "\n" for line in codecs.open(fName, encoding='cp1251', errors='replace')]
        parse_panel = get_panel(sublime.active_window().active_view(), "".join(lines), name_panel=pref + relative_path)
        names_import = [parse_panel.substr(i) + '.mac' for i in parse_panel.find_by_selector('import.file.mac')]
        for x in parse_panel.find_by_selector(
                'variable.declare.name.mac - (meta.class.mac, meta.macro.mac), entity.name.function.mac - meta.class.mac, meta.class.mac entity.name.class.mac'):
            if 'entity.name.function.mac' in parse_panel.scope_name(x.a):
                region = [i for i in parse_panel.find_by_selector('meta.macro.mac') if i.contains(x)]
                name_param = [parse_panel.substr(i) for i in parse_panel.find_by_selector('variable.parameter.macro.mac') if region[0].contains(i)]
                hint = ", ".join(["${%s:%s}" % (k + 1, v.strip()) for k, v in enumerate(name_param)])
                names_global.append((parse_panel.substr(x) + '(...)\t' + basename(fName), parse_panel.substr(x) + '(' + hint + ')'))
            else:
                names_global.append((parse_panel.substr(x) + '\t' + basename(fName), parse_panel.substr(x)))
        if relative_path == 'Mac/System/CO/CommonVariables.mac':
            log(ID, names_global)
        sublime.active_window().destroy_output_panel(pref + relative_path)
        return names_import, names_global

    def parse_xml(self, file, extension):
        """ Кэшируем метаданные
        """
        if extension != 'xml':
            return []
        if not file:
            verbose(ID, 'Нет файла для анализа')
            return []
        lines = [line for line in codecs.open(file, encoding='cp1251', errors='replace')]
        root = ET.fromstring("".join(lines))
        for o in root.findall("./object"):
            self.meta_data[o.get('Name')] = {'type': 'Object', 'Fields': [], 'Methods': [], 'Keys': []}
            for f in o.findall("Field"):
                self.meta_data[o.get('Name')]['Fields'] += [f.get('Name')]
            for m in o.findall("Method"):
                self.meta_data[o.get('Name')]['Methods'] += [m.get('Name')]
            for k in o.findall("Key"):
                self.meta_data[o.get('Name')]['Keys'] += [k.get('Name')]

    def run(self):
        verbose(ID, "START adding files in", self.folder)
        t = time.time()
        # load from tempfile
        # self.load_from_cache()
        # indexing
        progress_bar = ProgressBar("RSBIDE: Индексация файлов проекта")
        progress_bar.start()
        self.files = self.read(self.folder)
        progress_bar.stop()
        # self.files['last_scan'] = time.ctime(time.time())
        deleted = list(set(self.files.keys()) - set(self.not_delete))
        for key in deleted:
            self.files.pop(key, True)
            log(ID, 'delete', key)
        # save to tempfile
        self.save_to_cache()
        log("Files in cache:", len(self.files),
            "Scan Time:", str(time.time() - t),
            "Add to cache:", len(self.last_add)
            )

    def read(self, folder, base=None):
        """return all files in folder"""
        folder_cache = self.files
        base = base if base is not None else folder
        # test ignore expressions on current path
        for test in self.exclude_folders:
            if re.search('(?i)' + test, folder) is not None:
                verbose(ID, "skip " + folder)
                return folder_cache

        # ressources = os.listdir(folder)
        for ressource in os.listdir(folder):
            current_path = os.path.join(folder, ressource)
            if (os.path.isfile(current_path)):
                relative_path = os.path.relpath(current_path, base)
                filename, extension = os.path.splitext(relative_path)
                # posix required for windows, else absolute paths are wrong: /asd\ads\
                relative_path = re.sub("\$", config["ESCAPE_DOLLAR"], posix(relative_path))
                extension = extension[1:]
                if extension not in self.extensions:
                    continue
                self.not_delete += [relative_path]
                if folder_cache.get(relative_path, False) and folder_cache[relative_path][3].get(
                        'mtime', time.ctime(time.time())) == time.ctime(os.path.getmtime(current_path)):
                    continue
                self.last_add.append(posix(relative_path))
                log(ID, len(self.last_add), relative_path)
                imp = []
                glob = []
                if extension == 'xml' and 'TI/' in relative_path:
                    self.parse_xml(posix(current_path), extension)
                else:
                    imp, glob = self.parse_import(relative_path, posix(current_path), extension)
                folder_cache[relative_path] = [
                    # modified filepath. $ hack is reversed in post_commit_completion
                    re.sub("\$", config["ESCAPE_DOLLAR"], posix(filename)),
                    # extension of file
                    extension,
                    # sublime completion text
                    posix(filename) + "\t" + extension,
                    {
                        'fullpath': posix(current_path),
                        'mtime': time.ctime(os.path.getmtime(current_path)),
                        'imports': imp,
                        'globals': glob
                    }
                ]

            elif (not ressource.startswith('.') and os.path.isdir(current_path)):
                folder_cache.update(self.read(current_path, base))
        return folder_cache
