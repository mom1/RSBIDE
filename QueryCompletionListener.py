# -*- coding: utf-8 -*-
# @Author: mom1
# @Date:   2016-07-30 17:19:44
# @Last Modified by:   MOM
# @Last Modified time: 2016-08-07 19:06:31
import sublime_plugin

from RSBIDE.RsbIDE import RSBIDE
from RSBIDE.RsbIDE import is_RStyle_view


ID = "QCL"


class QueryCompletionListener(sublime_plugin.EventListener):

    # tracks on_post_insert_completion
    track_insert = {
        "active": False,
        "start_line": "",
    }
    post_remove = ""

    def on_query_completions(self, view, prefix, locations):
        if is_RStyle_view(view, locations):
            return (RSBIDE.get_completions(view, prefix), 0)
        return ([], 0)
