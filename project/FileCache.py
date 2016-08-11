# -*- coding: utf-8 -*-
import sublime
import os
import re
from RSBIDE.common.verbose import verbose
from RSBIDE.common.verbose import log
import RSBIDE.common.path as Path
from collections import OrderedDict
from RSBIDE.project.FileCacheWorker import FileCacheWorker

ID = "search"
ID_CACHE = "cache"


def posix(path):
    return path.replace("\\", "/")


class FileCache:
    """
        Manages path suggestions by loading, caching and filtering project files. Add folders by
        `add(<path_to_parent_folder>)`
    """

    def __init__(self, file_extensions, exclude_folders, directory):
        self.directory = directory
        self.valid_extensions = file_extensions
        self.exclude_folders = exclude_folders
        self.cache = None

        self.rebuild()

    def __len__(self):
        if self.cache and self.cache.files:
            return len(self.cache.files)
        else:
            return 0

    def update_settings(self, file_extensions, exclude_folders):
        self.valid_extensions = file_extensions
        self.exclude_folders = exclude_folders

    def search_completions(self, needle, project_folder, valid_extensions, base_path=False):
        """
            retrieves a list of valid completions, containing fuzzy searched needle

            Parameters
            ----------
            needle : string -- to search in files
            project_folder : string -- folder to search in, cached via add
            valid_extensions : array -- list of valid file extensions
            base_path : string -- of current file, creates a relative path if not False
            with_extension : boolean -- insert extension

            return : List -- containing sublime completions
        """
        project_files = self.cache.files
        if (project_files is None):
            return False

        # basic: strip any dots
        needle = re.sub("\.\./", "", needle)
        needle = re.sub("\.\/", "", needle)
        # remove starting slash
        needle = re.sub("^\/", "", needle)
        # cleanup
        needle = re.sub('["\'\(\)$]', '', needle)
        # prepare for regex extension string
        needle = re.escape(needle)

        # build search expression
        regex = ".*"
        for i in needle:
            regex += i + ".*"

        verbose(ID, "scan", len(project_files), "files for", needle, valid_extensions)

        # get matching files
        result = []
        for filepath in project_files:
            properties = project_files.get(filepath)
            """
                properties[0] = escaped filename without extension, like "test/mock/project/index"
                properties[1] = file extension, like "html"
                properties[2] = file displayed as suggestion, like 'test/mock/project/index     html'
            """
            if (
                (
                    properties[1] in valid_extensions or "*" in valid_extensions) and
                    re.match(regex, filepath, re.IGNORECASE)):
                completion = self.get_completion(filepath, properties[2], base_path)
                result.append(completion)

        return (result, sublime.INHIBIT_EXPLICIT_COMPLETIONS | sublime.INHIBIT_WORD_COMPLETIONS)

    def find_file(self, file_name):
        if self.cache:
            project_files = self.cache.files
        else:
            return {}
        if (project_files is None):
            return False

        result = {}
        file_name_query = r".*\b" + re.escape(file_name) + ".*"
        for filepath, val in project_files.items():
            if re.match(file_name_query, filepath, re.IGNORECASE):
                result[filepath] = val
        result = OrderedDict(sorted(result.items(), key=lambda t: t[0]))
        return result

    def get_completion(self, target_path, path_display, base_path=False):
        if base_path is False:
            # absolute path
            return (target_path, "/" + target_path)
        else:
            # create relative path
            return (target_path, Path.trace(base_path, target_path))

    def get_all_list_metadate(self):
        """ Return all types from metadata
        """
        if not self.cache:
            return
        result = []
        for x, val in self.cache.meta_data.items():
            result += [(x + '\t' + val['type'], x)]
            result += [(i + '\t' + 'Field', i) for i in val['Fields']]  # if (i + '\t' + 'Field', i) not in result
            result += [(i + '\t' + 'Method', i) for i in val['Methods']]  # if (i + '\t' + 'Method', i) not in result
            result += [(i + '\t' + 'Key', i) for i in val['Keys']]  # if (i + '\t' + 'Key', i) not in result
        log(ID, len(result))
        return result

    def file_is_cached(self, file_name):
        """ returns False if the given file is not within cache
            tests files with full path or relative from project directory
        """
        name, extension = os.path.splitext(file_name)
        extension = extension[1:]
        if extension not in self.valid_extensions:
            verbose(ID_CACHE, "file to cache has no valid extension", extension)
            return True

        file_name = re.sub(self.directory, "", file_name)
        return self.cache.get(file_name, False) is not False

    def rebuild(self):
        self.cache = FileCacheWorker(self.exclude_folders, self.valid_extensions, self.directory)
        self.cache.start()
