from app.services.harbor_client import _quote_repository_name, _split_repository


def test_split_repository_uses_first_path_segment_as_project():
    assert _split_repository("project/nested/repository") == ("project", "nested/repository")


def test_quote_repository_name_double_encodes_slashes_for_harbor_path_params():
    assert _quote_repository_name("nested/repository") == "nested%252Frepository"
