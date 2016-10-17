# -*- coding: utf-8 -*-
# import sublime
import sublime_plugin

from RSBIDE.common.verbose import verbose
from RSBIDE.project.CurrentFile import CurrentFile
from RSBIDE.project.ProjectManager import ProjectManager
from RSBIDE.common.lint import Linter

ID = "CurrentFileListener"


class CurrentFileListener(sublime_plugin.EventListener):
    """ Evaluates and caches current file`s project status """

    def on_modified_async(self, view):
        Linter(view).erase_all_regions()

    def on_post_save_async(self, view):
        project = ProjectManager.get_current_project()
        if not project:
            return
        if CurrentFile.is_temp():
            verbose(ID, "temp file saved, reevaluate")
            CurrentFile.cache[view.id()] = None
        if project.get_setting("LINT_ON_SAVE", True):
            lint = Linter(view, ProjectManager)
            lint.start()
        if CurrentFile.is_valid():
            ProjectManager.rebuild_filecache()
        self.on_activated_async(view)

    def on_activated_async(self, view):
        # view has gained focus
        proj = ProjectManager.get_current_project()
        if not proj:
            return
        CurrentFile.evaluate_current(view, proj)
