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
from RSBIDE.common.verbose import log, warn
from RSBIDE.common.config import config
from RSBIDE.common.progress_bar import ProgressBar
import xml.etree.ElementTree as ET
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
IDc = "cache"


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
        self.files_cache = self.m.hexdigest() + '.' + IDc
        self.folder_cachew = self.m.hexdigest()
        self.last_add = []
        self.is_delete = False
        self.files = None
        self.meta_data = None
        self.load_from_cache()
        self.always_import = config['ALWAYS_IMPORT']

    def save_to_cache(self):
        if os.path.lexists(self.tmp_folder):
            with open(posix(os.path.join(self.tmp_folder, self.files_cache)), 'wb') as cache_file:
                pickle.dump((self.files, self.meta_data, self.class_struct), cache_file)
            verbose(IDc, 'cache save to ' + os.path.join(self.tmp_folder, self.files_cache))

    def load_from_cache(self):
        if os.path.lexists(os.path.join(self.tmp_folder, self.files_cache)):
            with open(posix(os.path.join(self.tmp_folder, self.files_cache)), 'rb') as cache_file:
                    try:
                        self.files, self.meta_data, self.class_struct = pickle.load(cache_file)
                        verbose(IDc, 'cache load from ' + os.path.join(self.tmp_folder, self.files_cache))
                    except Exception as e:
                        warn(IDc, e)
        else:
            self.files = {}
            self.meta_data = {}
            self.class_struct = {}

    def parse_file(self, relative_path, fName, extension):
        pref = 'RSBIDE:Parse_file_'  # Префикс для панели парсинга
        if extension != 'mac':
            return [], []
        if not fName or not relative_path:
            verbose(IDc, 'Нет файла для анализа')
            return [], []
        names_import = []
        names_global = []
        lines = [line.rstrip('\r\n') + "\n" for line in codecs.open(fName, encoding='cp1251', errors='replace')]
        parse_panel = get_panel(sublime.active_window().active_view(), "".join(lines), name_panel=pref + relative_path)
        names_import = [parse_panel.substr(i) + '.mac' for i in parse_panel.find_by_selector('import.file.mac')]
        # globals
        for x in parse_panel.find_by_selector(
                'variable.declare.name.mac - (meta.class.mac, meta.macro.mac), entity.name.function.mac - meta.class.mac, meta.class.mac entity.name.class.mac'
        ):
            if 'entity.name.function.mac' in parse_panel.scope_name(x.a):
                region = [i for i in parse_panel.find_by_selector('meta.macro.mac') if i.contains(x)]
                name_param = [parse_panel.substr(i) for i in parse_panel.find_by_selector('variable.parameter.macro.mac') if region[0].contains(i)]
                hint = ", ".join(["${%s:%s}" % (k + 1, v.strip()) for k, v in enumerate(name_param)])
                names_global.append((parse_panel.substr(x) + '(...)\t' + 'global', parse_panel.substr(x) + '(' + hint + ')'))
            else:
                names_global.append((parse_panel.substr(x) + '\t' + 'global', parse_panel.substr(x)))
        # class struktura
        for mc in parse_panel.find_by_selector('meta.class.mac'):
            for x in parse_panel.find_by_selector('meta.class.mac entity.name.class.mac'):
                if not mc.contains(x):
                    continue
                self.class_struct[parse_panel.substr(x)] = {'file': relative_path, 'parent': None, 'variable': [], 'macro': []}
                for i in parse_panel.find_by_selector(
                    'entity.other.inherited-class.mac, meta.class.mac variable.declare.name.mac, meta.class.mac entity.name.function.mac'
                ):
                    if not mc.contains(i):
                        continue
                    if 'entity.other.inherited-class.mac' in parse_panel.scope_name(i.a):
                        self.class_struct[parse_panel.substr(x)]['parent'] = parse_panel.substr(i)
                    elif 'variable.declare.name.mac' in parse_panel.scope_name(i.a):
                        self.class_struct[parse_panel.substr(x)]['variable'].append(
                            (parse_panel.substr(i) + '\t' + parse_panel.substr(x), parse_panel.substr(i)))
                    elif 'entity.name.function.mac' in parse_panel.scope_name(i.a):
                        region = [m for m in parse_panel.find_by_selector('meta.macro.mac') if m.contains(i)]
                        name_param = [parse_panel.substr(j) for j in parse_panel.find_by_selector('variable.parameter.macro.mac') if region[0].contains(j)]
                        hint = ", ".join(["${%s:%s}" % (k + 1, v.strip()) for k, v in enumerate(name_param)])
                        self.class_struct[parse_panel.substr(x)]['macro'].append(
                            (parse_panel.substr(i) + '(...)\t' + parse_panel.substr(x), parse_panel.substr(i) + '(' + hint + ')'))
        sublime.active_window().destroy_output_panel(pref + relative_path)
        return names_import, names_global

    def parse_xml(self, file, extension, relative_path):
        """ Кэшируем метаданные
        """
        if extension != 'xml':
            return []
        if not file or not relative_path:
            verbose(IDc, 'Нет файла для анализа')
            return []
        lines = [line for line in codecs.open(file, encoding='cp1251', errors='replace')]
        root = ET.fromstring("".join(lines))
        for o in root.findall("./object"):
            self.meta_data[o.get('Name')] = {'type': 'Object', 'file': relative_path, 'Fields': [], 'Methods': [], 'Keys': []}
            for f in o.findall("Field"):
                self.meta_data[o.get('Name')]['Fields'] += [f.get('Name')]
            for m in o.findall("Method"):
                self.meta_data[o.get('Name')]['Methods'] += [m.get('Name')]
            for k in o.findall("Key"):
                self.meta_data[o.get('Name')]['Keys'] += [k.get('Name')]

    def run(self):
        verbose(IDc, "START adding files in", self.folder)
        t = time.time()
        # indexing
        progress_bar = ProgressBar("RSBIDE: Индексация файлов проекта")
        progress_bar.start()
        try:
            # self.files =
            self.read(self.folder)
        except Exception as e:
            warn(IDc, e)
            progress_bar.stop()
        finally:
            progress_bar.stop()

        if len(self.last_add) > 0 or self.is_delete:
            self.save_to_cache()
        log("Files in cache:", len(self.files),
            "Scan Time:", str(time.time() - t),
            "Add to cache:", len(self.last_add)
            )

    def all_files_in_folders(self, folder, base=None):
        all_files = []
        base = base if base is not None else folder
        for test in self.exclude_folders:
            if re.search('(?i)' + test, folder) is not None:
                return all_files
        for x in os.listdir(folder):
            current_path = os.path.join(folder, x)
            if (os.path.isfile(current_path)):
                extension = os.path.splitext(current_path)[1]
                if extension[1:] not in self.extensions:
                    continue
                all_files.append(posix(current_path))
            elif (not x.startswith('.') and os.path.isdir(current_path)):
                all_files += self.all_files_in_folders(current_path, base)
        return all_files

    def add_file(self, path, base):
        relative_path = os.path.relpath(path, base)
        filename, extension = os.path.splitext(relative_path)
        relative_path = re.sub("\$", config["ESCAPE_DOLLAR"], posix(relative_path))
        self.last_add.append(posix(relative_path))
        log(IDc, len(self.last_add), relative_path)
        imp = []
        glob = []
        extension = extension[1:]
        if extension == 'xml' and 'TI/' in relative_path:
            self.parse_xml(posix(path), extension, relative_path)
        else:
            imp, glob = self.parse_file(relative_path, posix(path), extension)
        self.files[relative_path] = [
            # modified filepath. $ hack is reversed in post_commit_completion
            re.sub("\$", config["ESCAPE_DOLLAR"], posix(filename)),
            # extension of file
            extension,
            # sublime completion text
            posix(filename) + "\t" + extension,
            {
                'fullpath': posix(path),
                'mtime': time.ctime(os.path.getmtime(path)),
                'imports': imp,
                'globals': glob
            }
        ]

    def read(self, folder):
        """return all files in folder"""
        folder_cache = self.files
        # test ignore expressions on current path
        for test in self.exclude_folders:
            if re.search('(?i)' + test, folder) is not None:
                verbose(IDc, "skip " + folder)
                return {}
        # The set of all paths in the index
        indexed_paths = set()
        # The set of all paths we need to re-index
        to_index = set()
        # Loop over the stored fields in the index
        for key, val in folder_cache.items():
            indexed_path = val[3].get('fullpath')
            indexed_paths.add(indexed_path)
            if not os.path.exists(indexed_path):
                # This file was deleted since it was indexed
                self.files.pop(key, True)
                self.is_delete = True
                for_del = set()
                for x, val in self.meta_data.items():
                    if val['file'] != key:
                        continue
                    for_del.add(x)
                for x in for_del:
                    self.meta_data.pop(x, True)
                for_del = set()
                for x, val in self.class_struct.items():
                    if val['file'] != key:
                        continue
                    for_del.add(x)
                for x in for_del:
                    self.class_struct.pop(x, True)
                log(IDc, 'delete', key)
            else:
                # Check if this file was changed since it
                # was indexed
                indexed_time = val[3].get('mtime', time.ctime(time.time()))
                mtime = time.ctime(os.path.getmtime(indexed_path))
                if mtime == indexed_time:
                    continue
                    # The file has changed, delete it and add it to the list of
                    # files to reindex
                to_index.add(indexed_path)
        # Loop over the files in the filesystem
        for path in self.all_files_in_folders(folder):
            if path in to_index or path not in indexed_paths:
                # This is either a file that's changed, or a new file
                # that wasn't indexed before. So index it!
                self.add_file(path, folder)
