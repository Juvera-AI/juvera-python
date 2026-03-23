# tests/test_version.py
def test_version_attribute_exists():
    import juvera_sdk
    assert hasattr(juvera_sdk, "__version__")
    assert juvera_sdk.__version__ == "0.1.5"
