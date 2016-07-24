import os
import re
import time
import threading
import hashlib
import pickle
from RSBIDE.common.verbose import verbose
from RSBIDE.common.config import config
"""
    Scans, parses and stores all files in the given folder to the dictionary `files`

    Each file entry is set by its relative `filepath` and holds an array like
        0 : filename (modified)
        1 : file extension
        2 : sublime text auto completion string
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
        self.files = None
        self.tmp_folder = os.path.expandvars(r'%TEMP%')
        self.m = hashlib.md5()
        self.m.update(self.folder.encode('utf-8'))
        self.files_cache = self.m.hexdigest() + '.' + ID

    def save_to_cache(self):
        if os.path.lexists(self.tmp_folder):
            with open(os.path.join(self.tmp_folder, self.files_cache), 'wb') as cache_file:
                pickle.dump(self.files, cache_file)
            verbose(ID, 'cache save to ' + os.path.join(self.tmp_folder, self.files_cache))

    def load_from_cache(self):
        if os.path.lexists(os.path.join(self.tmp_folder, self.files_cache)):
            with open(os.path.join(self.tmp_folder, self.files_cache), 'rb') as cache_file:
                    try:
                        self.files = pickle.load(cache_file)
                        verbose(ID, 'cache load from ' + os.path.join(self.tmp_folder, self.files_cache))
                    except Exception:
                        pass
                        # os.remove(cache_file)

    def run(self):
        verbose(ID, "START adding files in", self.folder)
        t = time.time()
        # load from tempfile
        self.load_from_cache()
        # indexing
        self.files = self.read(self.folder)
        # save to tempfile
        self.save_to_cache()
        verbose(ID, len(self.files), "files cached", "Time", str(time.time() - t))

    def read(self, folder, base=None):
        """return all files in folder"""
        folder_cache = {}
        base = base if base is not None else folder
        # test ignore expressions on current path
        for test in self.exclude_folders:
            if re.search('(?i)' + test, folder) is not None:
                verbose(ID, "skip " + folder)
                return folder_cache

        # ressources =
        for ressource in os.listdir(folder):
            current_path = os.path.join(folder, ressource)
            if (os.path.isfile(current_path)):
                relative_path = os.path.relpath(current_path, base)
                filename, extension = os.path.splitext(relative_path)
                extension = extension[1:]

                # posix required for windows, else absolute paths are wrong: /asd\ads\
                relative_path = re.sub("\$", config["ESCAPE_DOLLAR"], posix(relative_path))
                if extension in self.extensions:
                    folder_cache[relative_path] = [
                        # modified filepath. $ hack is reversed in post_commit_completion
                        re.sub("\$", config["ESCAPE_DOLLAR"], posix(filename)),
                        # extension of file
                        extension,
                        # sublime completion text
                        posix(filename) + "\t" + extension
                    ]

            elif (not ressource.startswith('.') and os.path.isdir(current_path)):
                folder_cache.update(self.read(current_path, base))
        return folder_cache
