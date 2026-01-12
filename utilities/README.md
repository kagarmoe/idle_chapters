# Utilities

## Updating assets

After you make a schema change, update the corresponding assets file.

In the IDE:

```py
from utilities import update_assets

update_assets.update_asset_file()
```

## Backfilling blank fields with ChatGPT

If you want cozy filler text for empty fields in `assets/<name>.json`, use the ChatGPT helper. `update_asset_file()` now returns a dict mapping asset files to the fields it added, so you can pass that dict straight into `backfill_all_assets` to avoid rerunning assets that already matched their schema.

```py
from utilities.backfill_assets import backfill_assets

updated = backfill_assets("collectibles")
print(updated)
```

It reads the tone contract (`dev/game_design/tone_contract.md`) and all `lexicons/*.json` files to build a prompt, so keep those files up to date. The helper expects `OPENAI_API_KEY` in your environment and uses the OpenAI chat API to generate replacement strings for any blank string fields (e.g. `notes`, `cozy_association`). The returned list tells you which item paths were modified.

### Backfill everything

To run the helper across every `assets/*.json`, leave the `model`/`temperature` defaults and call:

```py
from utilities.backfill_assets import backfill_all_assets

from utilities import update_assets

updated_assets = update_assets.update_asset_file()
overall_updates = backfill_all_assets(updated_assets=updated_assets, exclude=["session"])
print(overall_updates)
```

`backfill_all_assets` returns a dict mapping asset stems to the dotted field paths that were populated; use `exclude` (just the stem, without `.json`) if you need to skip large files. It reuses the cached `ChatGPTQuery` so repeated calls stay affordable.


### Cost controls

`utilities/chatgpt_query.py` wraps OpenAI calls with shared defaults (model=`gpt-4o-mini`, temperature=`0.3`), per-prompt caching in `.chatgpt_cache.json`, and consistent usage reporting so you can reuse results without rerunning the API. Pass a custom `ChatGPTQuery` into `backfill_assets` if you need tighter controls or want to reuse the cache across multiple helpers.
