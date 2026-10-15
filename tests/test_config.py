from pathlib import Path

import pytest

from src.config import load_config


def test_loads_example_config():
    config = load_config("config.example.yaml")
    assert len(config.schools) == 2
    elementary = next(s for s in config.schools if s.name == "Example Elementary")
    assert [c.name for c in elementary.relevant_classes] == ["Room 12", "Room 5"]
    assert config.rules.deadline_window_days == 7


def test_grade_note_is_per_class_not_per_school():
    """This is the exact bug that broke: two classes at the same school,
    each needing its own grade note — used to only fit one per school."""
    config = load_config("config.example.yaml")
    elementary = next(s for s in config.schools if s.name == "Example Elementary")
    room12 = next(c for c in elementary.relevant_classes if c.name == "Room 12")
    room5 = next(c for c in elementary.relevant_classes if c.name == "Room 5")
    assert room12.grade_note == "3rd grade"
    assert room5.grade_note == "5th grade"


def test_plain_string_classes_still_work_without_a_grade_note():
    config = load_config("config.example.yaml")
    preschool = next(s for s in config.schools if s.name == "Example Preschool")
    names = [c.name for c in preschool.relevant_classes]
    assert names == ["Pandas", "Penguins"]
    assert all(c.grade_note is None for c in preschool.relevant_classes)


def test_schools_block_renders_readable_text():
    config = load_config("config.example.yaml")
    block = config.schools_block()
    assert "Example Elementary" in block
    assert "Room 12" in block
    assert "3rd grade" in block
    assert "Room 5" in block
    assert "5th grade" in block
    assert "Pandas" in block
    assert "Penguins" in block


def test_all_relevant_classes_flattens_across_schools():
    config = load_config("config.example.yaml")
    classes = config.all_relevant_classes()
    assert set(classes) == {"Room 12", "Room 5", "Pandas", "Penguins"}


def _write_config_with_storage(tmp_path, storage_yaml: str):
    """The example config, with its storage section swapped out."""
    text = Path("config.example.yaml").read_text()
    text = text[: text.index("storage:")] + storage_yaml
    path = tmp_path / "config.yaml"
    path.write_text(text)
    return path


def test_example_config_is_local_only_by_default():
    config = load_config("config.example.yaml")
    assert config.drive_folder_id is None


def test_drive_folder_id_is_read_from_config(tmp_path):
    path = _write_config_with_storage(
        tmp_path, 'storage:\n  db_path: "data/x.db"\n  drive_folder_id: "abc123"\n'
    )
    assert load_config(path).drive_folder_id == "abc123"


def test_missing_drive_folder_id_key_fails_loudly(tmp_path):
    """An older config.yaml from before this setting existed must not
    silently become local-only — that would quietly abandon a shared
    Drive-synced dedup history and start re-posting old items."""
    path = _write_config_with_storage(tmp_path, 'storage:\n  db_path: "data/x.db"\n')
    with pytest.raises(ValueError, match="drive_folder_id"):
        load_config(path)


def test_name_words_splits_school_and_class_names():
    from src.config import ClassInfo, School
    config = load_config("config.example.yaml")
    config.schools = [School(name="Example Elementary", type="K-5",
                             relevant_classes=[ClassInfo(name="Room 12"), ClassInfo(name="Pandas")])]
    assert config.name_words() == {"example", "elementary", "room", "12", "pandas"}
