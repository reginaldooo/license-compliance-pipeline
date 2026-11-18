from license_pipeline import config


def test_catalog_exists():
    assert config.CATALOG_PATH.exists()


def test_renewal_windows_sorted():
    assert list(config.RENEWAL_WINDOWS_DAYS) == sorted(config.RENEWAL_WINDOWS_DAYS)
