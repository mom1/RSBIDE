# RSBIDE

*[English version of the documentation](readme.md)*

Этот плагин добавляет IDE-шные функции для RS-Balance 3 в Sublime Text 3

![SublimeRStyle](https://raw.github.com/mom1/RSBIDE/master/screenshot/SublimeRStyle.jpg)

Особенности
------------

* **Авто-дополнение**
    * Переменные/Функции/Классы/Параметры класса/параметры функций дополняются с учетом обалсти видимости
    * Вместе с именем функции подставляются ее возможные параметры
    * Авто-дополнение Object/Field/Method/Key из *.xml (RSTypeInfo)
    * Авто-дополнение не чувствительно к регистру
    * Авто-дополнение в области import (подсказываются только не импортированные файлы из проекта)
    ![GotoPanel](https://raw.github.com/mom1/RSBIDE/master/screenshot/Completion_Import.jpg)
* **Перейти к объявлению и обратно**
    * Перейти к определению  `macro name(param)`, `class(...) name (param)`, `var name`  с учетом области видимости клавиши по умолчанию <kbd>Alt + G</kbd>
    * Перейти к определению выделенных функций через <kbd>Alt + G</kbd>
    * Перейти к файлу из области import <kbd>Alt + G</kbd>
    * Перейти к родительскому классу <kbd>Alt + G</kbd>
    ![GotoMenu](https://raw.github.com/mom1/RSBIDE/master/screenshot/GotoMenu.jpg)
    * Посмотреть структуру `macro` или `class` или `var` в нижней панели <kbd>Alt + S</kbd>
    ![GotoPanel](https://raw.github.com/mom1/RSBIDE/master/screenshot/GotoPanel.jpg)
    * При просмотре в определениях вы всегда можете вернуться к исходной позиции с помощью <kbd>Esc</kbd>
* **Просмотр документации**
    * Если по <kbd>Alt + S</kbd> слово под курсором не найденно в индексе, то пытаемся найти в документации (Бета)
    ![DocPanel](https://raw.github.com/mom1/RSBIDE/master/screenshot/DocPanel.jpg)
* **DllRegister RS-Balance 3 для проектной папки**
    * Пункт контекстного меню "DllRegister RS-Balance 3" на папке, регистрирует dll
    * Выключена если в папке нет dll для регистрации RS-Balance 3
    * Отображает результат попытки регистрации в строке статуса
    ![DllRegister](https://raw.github.com/mom1/RSBIDE/master/screenshot/DllRegister_RS-Balance_3.jpg)
* **Подсветка синтаксиса**
    * Для .mac файлов
* **Подсветка замечаний из соглашения по разработке**
    * Все основные параметры вынесенны в настройки
    ![Linter](https://raw.github.com/mom1/RSBIDE/master/screenshot/Linter.jpg)
* **Запуск RS-Balance 3**
    * Быстрый запуск Клиентского приложения из проекта
    * Для быстрого запуска клиента с отладкой используйте <kbd>Ctrl + B</kbd>, <kbd>F7</kbd>
    * Для выбора варианта запуска используйте <kbd>Ctrl + Shift + B</kbd>:
        - RSInit (RSInit.exe)
        - RSInit - client -rsldebug
        - RSInit - $file_name -rsldebug
        - RSInit - $file_name -rsldebug -windowsauth
        - RSInit - client
        - RSInit - RPCserv.exe -c -cfg RPCServ.exe.rsconfig
        - RSInit - TerminalClient -rsldebug
        - RSInit - TypeInfo
        - RSInit - RSAdmin
* **Различные полезные Snippets**
    * Предопределенные языковые конструкции. Список будет пополняться конструкциями из [RSL](http://wiki.rs-balance.ru/index.php/RSL)
* **Другие команды**
    * RSBIDE: Вставить как строку - Вставляет скопированный текст как строку RSL. Если в целевом месте нет `;` то добавляет
    Пример: В буфер скопированна строка
    ```sql
    SELECT * FROM dbo.rdAnalyticSign ras
    WHERE ras.HasChild = 1 AND ras.ID NOT IN (SELECT DISTINCT COALESCE(ParentID,0)FROM rdAnalyticSign)
    ```
    ![PasteAsString](https://raw.github.com/mom1/RSBIDE/master/screenshot/PasteAsString.gif)
    * RSBIDE: Print Tree Import - Выводит дерево импортов текущего файла. Открывает в новой закладке

        ![PrintTreeImport](https://raw.github.com/mom1/RSBIDE/master/screenshot/PrintTreeImport.jpg)

Установка
------------
**Очень просто с помощью [Package Control](http://wbond.net/sublime_packages/package_control) прямо внутри Sublime Text 3 (Package Control должен быть установлен см. ссылку раздел InstallNow - ST3):**

1.  <kbd>Ctrl + Shift + P</kbd>
2.  Найти "install", нажать <kbd>Enter</kbd>
3.  Найти "RSBIDE", нажать <kbd>Enter</kbd>

**Вручную (не рекомендуется):**

1.  git Clone или скачайте этот пакет
2.  Положите его в каталог пакетов (найти каталог можно с помощью 'Preferences' -> 'Browse Packages...')


## plugins for RS-Balance 3

 * [rstylelint](https://github.com/mom1/SublimeLinter-contrib-rstylelint)
    * Проверка и подсветка синтаксических ошибок (с использованием rsl интерпретатора)
 * [RegExLink](https://github.com/mom1/RegExLink)
    * Открытие *.lbr файлов через контекстное меню дизайнером из проекта

Отличная [картинка](https://raw.github.com/mom1/RSBIDE/master/screenshot/ST_Key.png) для изучения основных комбинаций http://www.sublimetext.com/


Credits
-----
[MOM](https://github.com/mom1)
