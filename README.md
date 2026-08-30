# FoundryVTT-Babele-translator

## Workflow
babele_data<br/>
↓<br/>
extract_translatables_from_babele()<br/>
↓<br/>
01-translatables.json<br/>
↓<br/>
build_batches()<br/>
↓<br/>
02-batches.json<br/>
↓<br/>
translate_batches()<br/>
↓<br/>
04-translations-with-placeholders.json<br/>
↓<br/>
restore_placeholders()<br/>
↓<br/>
05-translations-final.json<br/>
↓<br/>
apply_translations()<br/>
↓<br/>
output.json<br/>