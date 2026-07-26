from configs.feature import LoginConfig


def test_platform_admin_emails_defaults_to_empty_string(monkeypatch) -> None:
    monkeypatch.delenv("PLATFORM_ADMIN_EMAILS", raising=False)

    assert LoginConfig().PLATFORM_ADMIN_EMAILS == ""


def test_platform_admin_emails_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv("PLATFORM_ADMIN_EMAILS", " Admin@Example.com,ops@example.com ")

    assert LoginConfig().PLATFORM_ADMIN_EMAILS == " Admin@Example.com,ops@example.com "


def test_login_config_has_only_one_platform_admin_setting() -> None:
    matching_fields = [name for name in LoginConfig.model_fields if "PLATFORM_ADMIN" in name]

    assert matching_fields == ["PLATFORM_ADMIN_EMAILS"]
