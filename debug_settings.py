# ───────────────────────────────────────────────────────────────
# save as debug_settings.py in project root and run: python debug_settings.py
# ───────────────────────────────────────────────────────────────
import json
from pathlib import Path
import pprint

from app.core.settings import _yaml_defaults, Settings, CFG_PATH

print(">> Reading YAML from:", CFG_PATH)
print(">> YAML exists:", CFG_PATH.exists())

defaults = _yaml_defaults()
print("\n>> _yaml_defaults() returned:")
pprint.pprint(defaults, sort_dicts=False)

settings = Settings(_secrets_dir=None, **defaults)

print("\n>> Final Settings object:")
print(json.dumps(settings.model_dump(), indent=2))
