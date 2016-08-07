config = {
    "DEBUG": False,
    "LOG": False,
    "RSB_SETTINGS_FILE": "RSBIDE.sublime-settings",
    "ESCAPE_DOLLAR": '\$',
    "TRIGGER_ACTION": ["auto_complete", "insert_path"],
    "INSERT_ACTION": ["commit_completion", "insert_best_completion"],
    "TRIGGER_STATEMENTS": ["prefix", "tagName", "style"],

    "BASE_DIRECTORY": False,
    "PROJECT_DIRECTORY": "",
    "DISABLE_AUTOCOMPLETION": False,
    "DISABLE_KEYMAP_ACTIONS": False,
    "AUTO_TRIGGER": True,
    "TRIGGER": [{
                "scope": "\\.mac\\s",
                "auto": True,
                "relative": True,
                "base_directory": False,
                "extensions": ["mac", "xml"],
                }],
    "EXCLUDE_FOLDERS": ["node\\_modules", "bower\\_components/.*/bower\\_components", "Web", "lbr", "DBFiles", "Script", "upgrader", "Template"],
    "ALWAYS_IMPORT": ["CommonVariables", "CommonDefines", "CommonClasses", "CommonFunctions", "CommonCallReference"],

    "POST_INSERT_MOVE_CHARACTERS": "^[\"\'\);]*"
}
