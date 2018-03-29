config = {
    # Сообщения в консоль
    "DEBUG": False,
    "LOG": False,
    # Linter
    "LINT": True,
    "MAXLENGTH": 160,
    "SHOW_SAVE": True,
    "SCOP_ERROR": "invalid.mac",
    "MAX_EMPTY_LINE": 2,
    "SHOW_CLASS_IN_STATUS": False,
    "MAX_DEPTH_LOOP": 5,
    "MAX_COUNT_MACRO_PARAM": 5,
    "LINT_ON_SAVE": True,
    "PREFIX_VARIABLE_GLOBAL": r"([msg]_)|(the)",
    "PREFIX_VARIABLE_VISUAL": r"(grid|grd)|(tree)|(fld)|(frm)|(dlg)|(btn)|(chk)|(radio|rd)|(edit|edt)|(list|lst)|(cmb)|(lbl|label)|(tab)|(cmd)|(control|ctrl)|(cl)",
    "PREFIX_VARIABLE_TYPE": r"(ref)|(ev)|(arr|tarr)|(o|obj)|(key)|(ax)|(dict)|(ds)|(i)|(s|str)|(is|b)|(f|lf)|(n|d|m)|(dt)|(t)|(v)|(pIn)|(oOut)",
    # Settings
    "RSB_SETTINGS_FILE": "RSBIDE.sublime-settings",
    # Кэш
    "EXCLUDE_FOLDERS": [
        "DBFiles", "DstLbr", "Export",
        "Help", "Html", "Import",
        "Lbr", "LoadDocum", "Log",
        "PKG", "Report", "RSM",
        "Script", "TaskLog", "Template",
        "Upgrader", "Web"],
    "ALWAYS_IMPORT": ["CommonVariables", "CommonDefines", "CommonClasses", "CommonFunctions", "CommonCallReference"],
    "BASE_DIRECTORY": False,
    "PROJECT_DIRECTORY": "",
    "TRIGGER": [{
                "scope": "\\.mac\\s",
                "auto": True,
                "relative": True,
                "base_directory": False,
                "extensions": ["mac", "xml"],
                }],
}
