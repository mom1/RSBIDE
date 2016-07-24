import sublime
import RSBIDE.common.path as Path
from RSBIDE.common.config import config
from RSBIDE.common.verbose import verbose


map_settings = {
    "TRIGGER": "scopes"
}


def project(window):
    """ returns project settings. If not already set, creates them """
    data = window.project_data()
    if not data:
        return False

    changed = False
    settings = data.get("settings", False)
    if settings is False:
        changed = True
        settings = {}
        data["settings"] = settings

    rsb_project_settings = settings.get("RSBIDE")
    if not rsb_project_settings:
        changed = True
        rsb_project_settings = {}
        settings["RSBIDE"] = rsb_project_settings
    if changed:
        window.set_project_data(data)

    return rsb_project_settings


def update():
    """ merges plugin settings with user settings by default """
    rsb_settings = sublime.load_settings(config["RSB_SETTINGS_FILE"])
    global_settings = merge(config, rsb_settings)

    if global_settings["BASE_DIRECTORY"]:
        global_settings["BASE_DIRECTORY"] = Path.sanitize_base_directory(global_settings["BASE_DIRECTORY"])

    if global_settings["PROJECT_DIRECTORY"]:
        global_settings[
            "PROJECT_DIRECTORY"] = Path.sanitize_base_directory(global_settings["PROJECT_DIRECTORY"])

    return global_settings


def merge(settings, overwrite):
    """ update settings by given overwrite """
    for key in settings:
        settings[key] = overwrite.get(key.lower(), settings[key])
    # support old config schema
    # for key in map_settings:
    #     mappedKey = map_settings[key]
    #     settings[key] = overwrite.get(mappedKey, settings[key])

    return settings
