import os
import sublime
from RSBIDE.common.config import config
# from RSBIDE.common.notice import *

proj_settings = None


def project(window):
    """ returns project settings. If not already set, creates them """
    data = window.project_data()
    if not data:
        return {}

    settings = data.get("settings", False)
    if settings is False:
        settings = {}

    rsb_project_settings = settings.get("RSBIDE", {})
    if not rsb_project_settings:
        rsb_project_settings = {}
    settings["RSBIDE"] = rsb_project_settings
    return rsb_project_settings


def update():
    """ merges plugin settings with user settings by default """
    rsb_settings = sublime.load_settings(config["RSB_SETTINGS_FILE"])
    global_settings = merge(config, rsb_settings)

    if global_settings["BASE_DIRECTORY"]:
        global_settings["BASE_DIRECTORY"] = os.path.dirname(global_settings["BASE_DIRECTORY"])

    if global_settings["PROJECT_DIRECTORY"]:
        global_settings[
            "PROJECT_DIRECTORY"] = os.path.dirname(global_settings["PROJECT_DIRECTORY"])

    return global_settings


def merge(settings, overwrite):
    """ update settings by given overwrite """
    for key in settings:
        settings[key] = overwrite.get(key.lower(), settings[key])
    return settings


def set_settings_project(settings):
    global proj_settings
    proj_settings = settings
