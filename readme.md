# RSBIDE

*[Русская версия документации](readme_ru.md)*

This plugin adds RS-Balance 3 completions and some IDE-like functions to Sublime Text 3

![SublimeRStyle](https://raw.github.com/mom1/RSBIDE/master/screenshot/SublimeRStyle.jpg)

Features
------------

* **auto-completions** 
    * The variables / functions / classes / class options / parameters functions are complemented in view of visibility obalsti
    * Together with the name of the function substituted its possible parameters
    * auto-completions Object/Field/Method/Key from *.xml (RSTypeInfo)
    * auto-completions are not case sensitive
    * Auto-completion in the import (not only tells the imported files from the project)
    ![GotoPanel](https://raw.github.com/mom1/RSBIDE/master/screenshot/Completion_Import.jpg)
* **Go to declaration and back again**
    * Go to Definition `macro name(param)`, `class(...) name (param)`, `var name` taking into account the scope default keys <kbd>Alt + G</kbd>
    * Go to the definition of the selected functions by <kbd>Alt + G</kbd>
    * Go to the file from the import <kbd> Alt + G </ kbd>
    * Go to the parent class
    ![GotoMenu](https://raw.github.com/mom1/RSBIDE/master/screenshot/GotoMenu.jpg)
    * Print Signature `macro` or `class` or `var` To Panel <kbd>Alt + S</kbd> 
    ![GotoPanel](https://raw.github.com/mom1/RSBIDE/master/screenshot/GotoPanel.jpg)
    * when browsing in the declarations you can always return to your starting position by using one of the above keys when nothing is under your cursor
* **Viewing documents**
    * If <kbd> Alt + S </kbd> word under the cursor is not found in the index, then try to find documentation (Beta)
    ![DocPanel](https://raw.github.com/mom1/RSBIDE/master/screenshot/DocPanel.jpg)
* **DllRegister RS-Balance 3 from project folder**
    * Folder context menu "DllRegister RS-Balance 3"
    * Disable if not folder RS-Balance 3
    * Show result registration in status line
    ![DllRegister](https://raw.github.com/mom1/RSBIDE/master/screenshot/DllRegister_RS-Balance_3.jpg)
* **Syntax highlighting**
    * For .mac files
* **Launch RS-Balance 3**
    * quickly open the Client with your Reg configuration
    * to Run Client use <kbd>Ctrl + B</kbd>, <kbd>F7</kbd> or search for it in the command palette.
    * use <kbd>Ctrl + Shift + B</kbd> to choice:
        - RSInit (RSInit.exe)
        - RSInit - client -rsldebug
        - RSInit - $file_name -rsldebug
        - RSInit - client
        - RSInit - RPCserv.exe -c -cfg RPCServ.exe.rsconfig
        - RSInit - TerminalClient -rsldebug
        - RSInit - TypeInfo
        - RSInit - RSAdmin
* **Various useful Snippets**
    * Predefined Snippets language features such as defaultproperties [RSL](http://wiki.rs-balance.ru/index.php/RSL)
* **Other commands**
    * Print Tree Import - It displays the current file tree imports. It opens in a new tab
    ![PrintTreeImport](https://raw.github.com/mom1/RSBIDE/master/screenshot/PrintTreeImport.jpg)

See Packages/RSBIDE/RSBIDE.sublime-settings for options. As with all ST packages, copy this file into your Packages/User folder and editing the copy there.

Installation
------------
**Very easy with [Package Control](http://wbond.net/sublime_packages/package_control) right inside Sublime Text 3 (Package Control needs to be installed):**

1.  <kbd>Ctrl + Shift + P</kbd>
2.  Search for "install", hit enter
3.  Search for "RSBIDE", hit enter

**Manually (not recommended):**

1.  Clone or download this package
2.  Put it into your Packages directory (find using 'Preferences' -> 'Browse Packages...')


## plugins for RS-Balance 3

 * [rstylelint](https://github.com/mom1/SublimeLinter-contrib-rstylelint)
    * Check and highlight syntax errors
 * [RegExLink](https://github.com/mom1/RegExLink)
    * Opening *.lbr files through the context menu of the project designer

ST3 only:
  [Sublime Text 3]: http://www.sublimetext.com/3

Credits
-----
[MOM](https://github.com/mom1)
