import json
from collections import Counter
from pathlib import Path

from dynamicprompts.generators import (
    CombinatorialPromptGenerator,
    RandomPromptGenerator,
)
from dynamicprompts.wildcards import WildcardManager
from dynamicprompts.wildcards.collection.structured import (
    _parse_structured_file_list,
    parse_structured_file,
)
from dynamicprompts.wildcards.item import WildcardItem


def _write_weighted_files(tmp_path: Path) -> tuple[Path, Path]:
    entries = [
        "2::{|navy} blue",
        "2::{|3::blood} red",
        "2::{lime|3::acid} green",
        "2.5::violet",
        "name::unchanged",
        "-2::unchanged",
        ".5::unchanged",
        "2.::unchanged",
        "prefix 2::unchanged",
    ]
    data = {"weighted": entries}
    json_path = tmp_path / "weights.json"
    yaml_path = tmp_path / "weights.yaml"
    json_path.write_text(json.dumps(data), encoding="utf-8")
    yaml_path.write_text(
        "weighted:\n" + "".join(f"  - {entry!r}\n" for entry in entries),
        encoding="utf-8",
    )
    return json_path, yaml_path


def _structured_values(path: Path):
    collections = dict(parse_structured_file(path))
    return collections["weighted"].get_values()


def test_structured_weights_are_leading_unsigned_numbers_only():
    entries = list(
        _parse_structured_file_list(
            [
                "2::{|navy} blue",
                "2::{|3::blood} red",
                "2::{lime|3::acid} green",
                "2.5::violet",
                "name::unchanged",
                "-2::unchanged",
                ".5::unchanged",
                "2.::unchanged",
                "prefix 2::unchanged",
            ],
        ),
    )

    assert entries[:4] == [
        WildcardItem(content="{|navy} blue", weight=2),
        WildcardItem(content="{|3::blood} red", weight=2),
        WildcardItem(content="{lime|3::acid} green", weight=2),
        WildcardItem(content="violet", weight=2.5),
    ]
    assert entries[4:] == [
        "name::unchanged",
        "-2::unchanged",
        ".5::unchanged",
        "2.::unchanged",
        "prefix 2::unchanged",
    ]


def test_json_and_yaml_structured_weights_are_identical(tmp_path: Path):
    json_path, yaml_path = _write_weighted_files(tmp_path)

    assert _structured_values(json_path) == _structured_values(yaml_path)


def test_random_generation_uses_structured_outer_weights(tmp_path: Path):
    (tmp_path / "weights.json").write_text(
        json.dumps({"weighted": ["1::light", "9::heavy"]}),
        encoding="utf-8",
    )
    manager = WildcardManager(path=tmp_path)
    generator = RandomPromptGenerator(manager, seed=0)

    prompts = generator.generate("__weighted__", num_images=100)
    counts = Counter(prompts)

    assert set(counts) == {"light", "heavy"}
    assert counts["heavy"] > counts["light"]


def test_combinatorial_generation_removes_only_outer_weight_prefix(tmp_path: Path):
    _write_weighted_files(tmp_path)
    manager = WildcardManager(path=tmp_path)
    generator = CombinatorialPromptGenerator(manager)

    prompts = generator.generate("__weighted__", max_prompts=None)

    assert set(prompts) == {
        " blue",
        "navy blue",
        " red",
        "blood red",
        "lime green",
        "acid green",
        "violet",
        "name::unchanged",
        "-2::unchanged",
        ".5::unchanged",
        "2.::unchanged",
        "prefix 2::unchanged",
    }
    assert all(not prompt.startswith(("2::", "2.5::")) for prompt in prompts)


def test_flat_structured_list_parses_outer_weights(tmp_path: Path):
    (tmp_path / "flat.json").write_text(
        json.dumps(["2::{|3::blood} red", "name::unchanged"]),
        encoding="utf-8",
    )
    (tmp_path / "flat2.yaml").write_text(
        "- '2::{|3::blood} red'\n- 'name::unchanged'\n",
        encoding="utf-8",
    )
    for path in (tmp_path / "flat.json", tmp_path / "flat2.yaml"):
        collection = dict(parse_structured_file(path))[path.stem]
        assert list(collection.get_values()) == [
            WildcardItem(content="{|3::blood} red", weight=2),
            "name::unchanged",
        ]
