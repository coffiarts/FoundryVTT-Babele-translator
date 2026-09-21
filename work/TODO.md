☐ = Todo
☑ = Done
☒ = Discarded

☑ ~~Bugfix: Intercept error when trying to translate a non-localization file in localization mode
    D:\projects\IntelliJ\FoundryVTT-Babele-translator\ct4f_translator.py", line 202
    D:\projects\IntelliJ\FoundryVTT-Babele-translator\ct4f_core_functions.py", line 650
    TypeError: expected string or bytes-like object, got 'list'~~

☑ ~~Bugfix: Vice versa: To also intercept when trying to translate a non-Babele file in Babele mode, add a generic check that aborts with msg when the input file yields zero translatables~~

☑ ~~Render status bars for terminology and translation (NEW_RUN and RESUME_MODE)~~

☑ ~~Auto-update status bars during processing~~

☑ ~~Refine concept for "Cancel" functionality and work_exception_handler:~~

- ~~when to show/hide "Cancel"~~
- ~~how/what to interrupt by "Cancel"~~
- ~~where to return to after "Cancel" or unexpected exceptions~~

☑ Handle the following specific exception scenarios explicitly (without hard-block/ErrorDialog):

- ~~CANCELLED => return to "prepared" state?~~

- ~~INVALID INPUT FILE (no lang file) => confirm with hint, return to "configuration" phase?~~

- ~~TRANSLATABLE TEXT EXCEEDS MAX_BATCH_SIZE => confirm with hint, return to preparation phase~~

- ~~CONFIGURATION MISMATCH => confirm with hint, allow to cleanup progress-info (like auto-triggering both "clear" buttons), then return to "prepared" phase~~

☑ ~~Improve readability of ErrorDialog contents (get rid of "technical noise", less stressful bg/fd colors)~~

☐ Visually improve confirmation prompts (currently clumsily placed inline, wiht ugly format, and not going away after being answered)

☐ Bugfix: Localization mode produces strict output filename <language>.json, dropping
any postfix from input file (like in en-US.json). Instead, it should keep the postfix, by only replacing the source language part of the name (e.g. "en") by the target language part (e.g. "de"): en-US.json => de-US.json

☐ Mock Mode should not create real Batch Statuses, to prevent that user is forced to reset them afterwards

☐ Disclose and persist setting: MAX_BATCH_SIZE

☐ Provide a more convenient output on successful completion (e.g. a message outside the log with a file link). Important: Also mention the Review Items file, if it exists!!

☐ In RESUME Mode: Also render "Project Size" and "Review Items" and "Status"

☐ Render popup details for each bar

☐ (optional?) Calculate and render "Status"

☐ Disclose and persist setting: SOURCE_LANGUAGE / TARGET_LANGUAGE

☐ Disclose and persist setting: GAME_SYSTEM_CONTEXT

☐ Disclose and persist setting: TRANSLATABLE_FIELDS => probably more complex, as it is a list

☐ Disclose and persist setting: TRANSLATABLE_CONTAINERS => same as above

☐ Settings: PROTECTED_SYNTAX_PATTERNS => same as above, plus: These are RegExp patterns that should probably be validated

☐ Improve readability of LogWindow content (make it collapsible, less stressful bg/fd colors)

☐ Animate current PROCESSING batch?



☐ UI Localization

☐ Use a CustomTkinter-Theme

☐ General review and refactoring of ct4f.run_translation() => split it up into better testable units?

☐ Split up ct4f_core_functions into more reasonable sub-libraries

### Just as a reminder: Frequently retest pyinstaller build:
    pyinstaller --onefile --windowed --add-data "assets:assets" --icon assets/icon.ico ct4f_app.py
    
    pyinstaller --onefile --windowed --add-data "assets:assets" --icon assets/icon.ico ct4f_app.py