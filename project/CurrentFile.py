# -*- coding: utf-8 -*-
import re
import os
import copy

from RSBIDE.common.verbose import verbose
from RSBIDE.common.verbose import log
import RSBIDE.common.parser as parser
import RSBIDE.common.path as Path

ID = "CurrentFile"


class CurrentFile:
    """ Evaluates and caches current file`s project status """

    cache = {}
    current = False
    default = {
        "is_temp": False,               # file does not exist in filesystem
        "directory": False,             # directory relative to project
        "project_directory": False     # project directory
    }

    def evaluate_current(view, project=None):
        cache = CurrentFile.cache.get(view.id())
        if cache:
            verbose(ID, "file cached", cache)
            CurrentFile.current = cache
            if project is not None and view.file_name() is not None and 'imports' not in CurrentFile.current:
                CurrentFile.current["imports"] = parser.get_import_tree(Path.posix(view.file_name()), project)
                CurrentFile.cache[view.id()] = CurrentFile.current
            return cache

        if not project:
            # not a project
            verbose(ID, "no project set")
            CurrentFile.current = CurrentFile.default
            return

        file_name = Path.posix(view.file_name())
        if not file_name:
            # not saved on disk
            CurrentFile.current = get_default()
            CurrentFile.current["is_temp"] = True
            CurrentFile.cache[view.id()] = CurrentFile.current
            verbose(ID, "file not saved")
            return

        project_directory = project.get_directory()
        if project_directory not in file_name:
            # not within project
            CurrentFile.current = CurrentFile.default
            verbose(ID, "file not within a project")
            return

        # add current view to cache
        CurrentFile.current = get_default()
        CurrentFile.current["project_directory"] = project_directory
        CurrentFile.current["directory"] = re.sub(project_directory, "", file_name)
        CurrentFile.current["directory"] = re.sub("^[\\\\/\.]*", "", CurrentFile.current["directory"])
        CurrentFile.current["directory"] = os.path.dirname(CurrentFile.current["directory"])
        if len(project.filecache) != 0:
            CurrentFile.current["imports"] = parser.get_import_tree(file_name, project)
            log(ID, 'imports count', len(CurrentFile.current["imports"]))

        verbose(ID, "File cached", file_name)
        CurrentFile.cache[view.id()] = CurrentFile.current

    def is_valid():
        return CurrentFile.current.get("project_directory") is not False

    def get_project_directory():
        return CurrentFile.current.get("project_directory")

    def get_directory():
        return CurrentFile.current.get("directory")

    def is_temp():
        return CurrentFile.current.get("is_temp")


def get_default():
    return copy.copy(CurrentFile.default)
