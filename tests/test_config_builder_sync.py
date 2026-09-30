"""Guards against tools/config-builder.html drifting out of sync with the
config format. The builder writes YAML by hand in JavaScript, so if a key
is added to config.example.yaml (and src/config.py) but not to the
builder, the builder would quietly produce configs that fail to load.

This doesn't run the page — it only checks that every key the example
config uses is one the builder actually writes. The full round trip
(builder output loaded by load_config) was checked by hand in a browser.
"""
from pathlib import Path

import yaml

BUILDER = Path("tools/config-builder.html")


def _all_keys(node) -> set[str]:
    keys: set[str] = set()
    if isinstance(node, dict):
        for k, v in node.items():
            keys.add(k)
            keys |= _all_keys(v)
    elif isinstance(node, list):
        for item in node:
            keys |= _all_keys(item)
    return keys


def test_builder_writes_every_key_the_example_config_uses():
    example = yaml.safe_load(Path("config.example.yaml").read_text())
    builder_source = BUILDER.read_text()
    missing = sorted(k for k in _all_keys(example) if f"{k}:" not in builder_source)
    assert not missing, (
        f"tools/config-builder.html never writes {missing} — update toYaml() "
        "there to match config.example.yaml"
    )
