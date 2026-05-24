# tests/test_version.py
import re


def test_version_attribute_exists():
    import juvera_sdk
    assert hasattr(juvera_sdk, "__version__")
    assert re.match(r"^\d+\.\d+\.\d+([.-].+)?$", juvera_sdk.__version__), (
        f"__version__={juvera_sdk.__version__!r} is not semver-shaped"
    )
