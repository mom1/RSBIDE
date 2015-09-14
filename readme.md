# RSBIDE

This plugin adds RS-Balance 3 completions and some IDE-like functions to Sublime Text 3

![SublimeRStyle](https://raw.github.com/mom1/RSBIDE/master/SublimeRStyle.jpg)

Features
------------

* **auto-completions** 
    * Functions according environment (import files)
    * Autocomplete Object/Field/Method from *.xml (RSTypeInfo)
    * Case insensitive completions
    * Parameter hints
* **Go to declaration and back again**
    * Go To Definition  `macro(...)` and `class(...) name (...)` according environment (import files) default key <kbd>Alt + G</kbd>
    * go to the declaration of the currently selected functions via <kbd>Alt + G</kbd>, <kbd>Ctrl + left click</kbd>
    * Print Signature `macro` and `class` To Panel <kbd>Alt + S</kbd> 

        ![GotoPanel](https://raw.github.com/mom1/RSBIDE/master/GotoPanel.jpg)
    * when browsing in the declarations you can always return to your starting position by using one of the above keys when nothing is under your cursor
* **DllRegister RS-Balance 3 from project folder**
    * Folder context menu "DllRegister RS-Balance 3"
    * Disable if not folder RS-Balance 3
    * Show result registration in status line
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
* **Various useful Snippets**
    * predefined Snippets language features such as defaultproperties [RSL](http://wiki.rs-balance.ru/index.php/RSL)

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

ST3 only:
  [Sublime Text 3]: http://www.sublimetext.com/3

Credits
-----
[MOM](https://github.com/mom1)
