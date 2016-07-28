# -*- coding: utf-8 -*-
import sublime
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
        self._LongLines(view)

    def _LongLines(self, view):
        return
        #  Settings  #
        project = ProjectManager.get_current_project()
        maxLength = project.get_setting("MAXLENGTH", 150)
        scope = "invalid.mac"
        firstCharacter_Only = False

        if 'R-Style' not in view.settings().get('syntax'):
            return
        view.erase_regions("LongLines")
        indentationSize = view.settings().get("tab_size")
        document = sublime.Region(0, view.size())
        lineRegions = view.lines(document)
        invalidRegions = []
        for region in lineRegions:
            text = view.substr(region)
            text_WithoutTabs = text.expandtabs(indentationSize)
            if text_WithoutTabs.isspace():
                tabOffset = 0
            else:
                tabDifference = len(text_WithoutTabs) - len(text)
                tabOffset = tabDifference
            lineLength = (region.end() - region.begin()) - tabOffset
            if lineLength > maxLength:
                highlightStart = region.begin() + (maxLength - tabOffset)
                if firstCharacter_Only is True:
                    highlightEnd = highlightStart + 1
                else:
                    highlightEnd = region.end()
                invalidRegion = sublime.Region(highlightStart, highlightEnd)
                invalidRegions.append(invalidRegion)
        if len(invalidRegions) > 0:
            view.add_regions("LongLines", invalidRegions, scope)

    def on_activated_async(self, view):
        # view has gained focus
        proj = ProjectManager.get_current_project()
        CurrentFile.evaluate_current(view, proj)
