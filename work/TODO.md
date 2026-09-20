☐ = Todo
☑ = Done
☒ = Discarded

☑ Bugfix: Intercept error when trying to translate a non-localization file in localization mode
    D:\projects\IntelliJ\FoundryVTT-Babele-translator\ct4f_translator.py", line 202
    D:\projects\IntelliJ\FoundryVTT-Babele-translator\ct4f_core_functions.py", line 650
    TypeError: expected string or bytes-like object, got 'list'

☑ Bugfix: Vice versa: To also intercept when trying to translate a non-Babele file in Babele mode, add a generic check that aborts with msg when the input file yields zero translatables

☐ Render status bars for terminology and translation (NEW_RUN and RESUME_MODE)

☐ In RESUME Mode: Also render "Project Size" and "Review Items" and "Status"

☐ Auto-update status bars during processing

☐ Render popup details for each bar

☐ (optional?) Calculate and render "Status"

☐ Bugfix: Localization mode produces strict output filename <language>.json, dropping
any postfix from input file (like in en-US.json). Instead, it should keep the postfix, by only replacing the source language part of the name (e.g. "en") by the target language part (e.g. "de"): en-US.json => de-US.json

☐ Improve translation dialog prompts (visualization, hide after answer)

☐ Settings: MAX_BATCH_SIZE

☐ Settings: SOURCE_LANGUAGE / TARGET_LANGUAGE

☐ Settings: GAME_SYSTEM_CONTEXT

☐ Settings: TRANSLATABLE_FIELDS => probably more complex, as it is a list

☐ Settings: TRANSLATABLE_CONTAINERS => same as above

☐ Settings: PROTECTED_SYNTAX_PATTERNS => same as above, plus: These are RegExp patterns that should probably be validated

☐ Improve readability of LogWindow (make it collapsible, less stressful bg/fd colors)

☐ and ErrorDialog contents (get rid of "technical noise", less stressful bg/fd colors)

☐ Handle INVALID INPUT FILE case explicitly (without ErrorDialog)

☐ Handle CancelledException explicitly (without ErrorDialog)

☐ UI Localization

☐ CustomTkinter-Theme

☐ General review and refactoring of ct4f.run_translation() => split it up into better testable units?

☐ Split up ct4f_core_functions into more reasonable sub-libraries

### Just as a reminder: Frequently retest pyinstaller build:
    pyinstaller --onefile --windowed --add-data "assets:assets" --icon assets/icon.ico ct4f_app.py
    
    pyinstaller --onefile --windowed --add-data "assets:assets" --icon assets/icon.ico ct4f_app.py