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
        self.files = None
        self.load_from_cache()

    def save_to_cache(self):
        if os.path.lexists(self.tmp_folder):
            with open(posix(os.path.join(self.tmp_folder, self.files_cache)), 'wb') as cache_file:
                pickle.dump(self.files, cache_file)
            verbose(ID, 'cache save to ' + os.path.join(self.tmp_folder, self.files_cache))

    def load_from_cache(self):
        if os.path.lexists(os.path.join(self.tmp_folder, self.files_cache)):
            with open(posix(os.path.join(self.tmp_folder, self.files_cache)), 'rb') as cache_file:
                    try:
                        self.files = pickle.load(cache_file)
                        verbose(ID, 'cache load from ' + os.path.join(self.tmp_folder, self.files_cache))
                    except Exception:
                        pass
                        os.remove(cache_file)
        else:
            self.files = {}

    def parse_import(self, relative_path, fName, extension):
        pref = 'RSBIDE:Parse_import_'  # Префикс для панели парсинга
        # for x, val in self.files.items():
        if extension != 'mac':
            return []
        if not fName or not relative_path:
            verbose(ID, 'Нет файла для анализа')
            return []
        names_import = []
        lines = [line.rstrip('\r\n') + "\n" for line in codecs.open(fName, encoding='cp1251', errors='replace')]
        parse_panel = get_panel(sublime.active_window().active_view(), "".join(lines), name_panel=pref + relative_path)
        names_import = [parse_panel.substr(i) + '.mac' for i in parse_panel.find_by_selector('import.file.mac')]
        sublime.active_window().destroy_output_panel(pref + relative_path)
        return names_import

    def run(self):
        verbose(ID, "START adding files in", self.folder)
        t = time.time()
        # load from tempfile
        # self.load_from_cache()
        # indexing
        self.files = self.read(self.folder)
        self.files['last_scan'] = time.ctime(time.time())
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
                extension = extension[1:]
                if extension not in self.extensions:
                    continue

                # posix required for windows, else absolute paths are wrong: /asd\ads\
                relative_path = re.sub("\$", config["ESCAPE_DOLLAR"], posix(relative_path))
                if folder_cache.get(relative_path, False) and folder_cache[relative_path][3].get(
                        'mtime', time.ctime(time.time())) == time.ctime(os.path.getmtime(current_path)):
                    continue
                self.last_add.append(posix(relative_path))
                log(ID, len(self.last_add), relative_path)
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
                        'imports': self.parse_import(relative_path, posix(current_path), extension)
                    }
                ]

            elif (not ressource.startswith('.') and os.path.isdir(current_path)):
                folder_cache.update(self.read(current_path, base))
        return folder_cache
