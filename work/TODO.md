☐ = Todo
☑ = Done
☒ = Discarded

### Bugfixes
☑ Intercept error when trying to translate a non-localization file in localization mode
    D:\projects\IntelliJ\FoundryVTT-Babele-translator\ct4f_translator.py", line 202
    D:\projects\IntelliJ\FoundryVTT-Babele-translator\ct4f_core_functions.py", line 650
    TypeError: expected string or bytes-like object, got 'list'
☑ Vice versa: To also intercept when trying to translate a non-Babele file in Babele mode, add a generic check that aborts with msg when the input file yields zero translatables

## Complete UI workflow
☐ Render status bars for terminology and translation (NEW_RUN and RESUME_MODE)
☐ In RESUME Mode: Also render "Project Size" and "Review Items" and "Status"
☐ Auto-update status bars during processing
☐ Render popup details for each bar
☐ (optional?) Calculate and render "Status"
☐ Improve translation dialog prompts (visualization, hide after answer)

### More settings to make editable and store in settings.json
(decide which ones to disclose in UI main window and which ones in setttings menu)
☐ MAX_BATCH_SIZE
☐ SOURCE_LANGUAGE / TARGET_LANGUAGE
☐ GAME_SYSTEM_CONTEXT
☐ TRANSLATABLE_FIELDS => probably more complex, as it is a list
☐ TRANSLATABLE_CONTAINERS => same as above
☐ PROTECTED_SYNTAX_PATTERNS => same as above, plus: These are RegExp patterns that should probably be validated

### UI details, Look & Feel
☐ Improve readability of LogWindow (make it collapsible, less stressful bg/fd colors)
☐ and ErrorDialog contents (get rid of "technical noise", less stressful bg/fd colors)
☐ Handle INVALID INPUT FILE case explicitly (without ErrorDialog)
☐ Handle CancelledException explicitly (without ErrorDialog)
☐ UI Localization
☐ CustomTkinter-Theme

### Other refactorings (lowest prio)
☐ General review and refactoring of ct4f.run_translation() => split it up into better testable units?
☐ Split up ct4f_core_functions into more reasonable sub-libraries

### Just as a reminder: Frequently retest pyinstaller build:
    pyinstaller --onefile --windowed --add-data "assets:assets" --icon assets/icon.ico ct4f_app.py
    
    pyinstaller --onefile --windowed --add-data "assets:assets" --icon assets/icon.ico ct4f_app.py