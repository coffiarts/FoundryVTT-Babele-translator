☐ = Todo
☑ = Done
☒ = Discarded

☑ Bugfix: Intercept error when trying to translate a non-localization file in localization mode
    D:\projects\IntelliJ\FoundryVTT-Babele-translator\ct4f_translator.py", line 202
    D:\projects\IntelliJ\FoundryVTT-Babele-translator\ct4f_core_functions.py", line 650
    TypeError: expected string or bytes-like object, got 'list'

☑ Bugfix: Vice versa: To also intercept when trying to translate a non-Babele file in Babele mode, add a generic check that aborts with msg when the input file yields zero translatables

☑ Render status bars for terminology and translation (NEW_RUN and RESUME_MODE)

☑ Auto-update status bars during processing

☑ Refine concept for "Cancel" functionality and work_exception_handler:

- when to show/hide "Cancel"
- how/what to interrupt by "Cancel"
- where to return to after "Cancel" or unexpected exceptions

☑ Handle the following specific exception scenarios explicitly (without hard-block/ErrorDialog):

- CANCELLED => return to "prepared" state?

- INVALID INPUT FILE (no lang file) => confirm with hint, return to "configuration" phase?

- TRANSLATABLE TEXT EXCEEDS MAX_BATCH_SIZE => confirm with hint, return to preparation phase

- CONFIGURATION MISMATCH => confirm with hint, allow to cleanup progress-info (like auto-triggering both "clear" buttons), then return to "prepared" phase

☑ Improve readability of ErrorDialog contents (get rid of "technical noise", less stressful bg/fd colors)

☑ Visually improve confirmation prompts (currently clumsily placed inline, with ugly format, and not going away after being answered)

☑ Special case: Refine "Placeholder Integrity Error" handling
- How to show the (potentially large) error output in an easy-to-read way
- How to handle closing of prompt window: "Yes", "No"?

☑ Bugfix: Localization mode produces strict output filename <language>.json, dropping
any postfix from input file (like in en-US.json). Instead, it should keep the postfix, by only replacing the source language part of the name (e.g. "en") by the target language part (e.g. "de"): en-US.json => de-US.json

☑ Mock Mode should not really change batch statuses, to prevent that user is forced to reset them afterwards and lose real progress

☑ Disclose and persist as setting: MAX_BATCH_SIZE

☑ Disclose and persist as setting: SOURCE_LANGUAGE / TARGET_LANGUAGE

☑ Disclose and persist as setting: GAME_SYSTEM_CONTEXT
- integrate a "system-agnostic" option!

☑ Now is the time for a general pimp of layout and style => maybe use a CustomTkinter-Theme

☑ on prepared: Render "Project Stats"

☑ Change Stats Box to multiline, so that Review Items line can be formatted in MAGENTA color

☑ Feature: When translation is completed successfully, the output (translated file plus review items file, if any) should be notified and made available conveniently through the status bar (bottom frame). At least the paths should be printed, but maybe (if technically possible) even a clickable link to the output dir?

☑ Feature: Evolve "Results Bar" into a "Status Bar" (maybe even rename it): Allow to populate it with meaningful intermediate status messages (idea: encapsulate this in a more generic function than show_results, like "show_status", and then make show_results use that function as well) 

☑ Feature: Play a sound on successful completion

☑ UX: Elaborate grid layout

☑ UX: Add background images

☑ UX: On clicking Stats Box->Review Items Counter, open Review Items list as Pop Out View

☑ UX: Visually emphasize Stats Info Box by a frame

☑ Refactoring: Cleanup scattered definitions and usage of color codes

☑ UX: Make the pop-out log auto-update like the inline log view, so that it can be kept open in parallel

☑ UX: Make disabled state of config widgets better recognizable

☑ UX: Rename "Reset" (Preparation) button to "Reconfigure" to make it more intuitive what it really does

☑ Feature: API client connection config -
- is it strictly OpenAI specific, or can we make it exchangeable via Settings?
- Disclose and persist LLM_MODEL setting

☑ Feature: Extend workflow by adding an option "Review terminology before translation", which stops after terminology is complete, providing the result in the same way as for the final translation (with a link to the terminology folder in the status bar). 

☑ UX: Add tooltips to essential UI elements (buttons, widgets, potentially truncated filepaths ...), including a new settings option to hide them.

☑ UX: UI Localization

☐ UX: Improve MBS slider

☐ Feature: Disclose and persist as "advanced" setting: TRANSLATABLE_FIELDS => probably more complex, as it is a list

☐ Feature: Disclose and persist as "advanced" setting: TRANSLATABLE_CONTAINERS => same as above

☐ Feature: Disclose and persist as "advanced" setting: PROTECTED_SYNTAX_PATTERNS => same as above, plus: These are RegExp patterns that should probably be validated

☐ Feature: Disclose and persist as "advanced" setting: TRANSLATION_INSTRUCTIONS and TERMINOLOGY_INSTRUCTIONS as user settings

☐ UX: "Reset to defaults" function

☐ Feature: Allow storing of setting presets

☐ UX: Cleanup/fix of Log view colors: Replace console colors by log colors (taking care not to break console coloring, if still needed)

☐ UX: Animate current PROCESSING batch?

☐ Refactoring: General review and rework of ct4f.run_translation() => split it up into better testable units?

☐ Refactoring: Split up ct4f_core_functions into more reasonable sub-libraries

☐ Make sure that all licensing/notice obligations are covered properly
- SIL fonts
- packages 
    pip-licenses --format=markdown
    pip install pip-licenses
- assets 

### Just as a reminder: Frequently retest pyinstaller build:
with console (for debugging):

    pyinstaller --onefile --add-data "assets:assets" --add-data "lang:lang" --icon assets/icon.ico ct4f_app.py

w/o console:

    pyinstaller --onefile --windowed --add-data "assets:assets" --add-data "lang:lang" --icon assets/icon.ico ct4f_app.py

