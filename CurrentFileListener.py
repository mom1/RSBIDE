# -*- coding: utf-8 -*-
# import sublime
import sublime_plugin

from RSBIDE.common.verbose import verbose
from RSBIDE.project.CurrentFile import CurrentFile
from RSBIDE.project.ProjectManager import ProjectManager
import RSBIDE.common.lint as Linter

ID = "CurrentFileListener"


class CurrentFileListener(sublime_plugin.EventListener):
    """ Evaluates and caches current file`s project status """

    def on_modified_async(self, view):
        Linter.erase_all_regions(view)

    def on_post_save_async(self, view):
        if CurrentFile.is_temp():
            verbose(ID, "temp file saved, reevaluate")
            CurrentFile.cache[view.id()] = None
        ProjectManager.rebuild_filecache()
        Linter.run_all_lint(view, ProjectManager)
        self.on_activated_async(view)

    def on_activated_async(self, view):
        # view has gained focus
        proj = ProjectManager.get_current_project()
        CurrentFile.evaluate_current(view, proj)
