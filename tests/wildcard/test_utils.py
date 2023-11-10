from dynamicprompts.wildcards.collection.structured import _parse_structured_file_list


def test_structured_parsing_emits_no_warnings(caplog):
    assert list(_parse_structured_file_list(["a", "b", "c"])) == ["a", "b", "c"]
    assert not caplog.records
