import sublime_plugin

from RSBIDE.common.verbose import verbose
from RSBIDE.project.CurrentFile import CurrentFile
from RSBIDE.project.ProjectManager import ProjectManager

ID = "CurrentFileListener"


class CurrentFileListener(sublime_plugin.EventListener):
    """ Evaluates and caches current file`s project status """

    def on_post_save_async(self, view):
        if CurrentFile.is_temp():
            verbose(ID, "temp file saved, reevaluate")
            CurrentFile.cache[view.id()] = None
            ProjectManager.rebuild_filecache()
            self.on_activated_async(view)

    def on_activated_async(self, view):
        # view has gained focus
        CurrentFile.evaluate_current(view, ProjectManager.get_current_project())
