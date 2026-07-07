from idle_chapters.main import parse_args


def test_default_is_not_verbose():
    assert parse_args([]).verbose is False


def test_long_flag():
    assert parse_args(["--verbose"]).verbose is True


def test_short_flag():
    assert parse_args(["-v"]).verbose is True
