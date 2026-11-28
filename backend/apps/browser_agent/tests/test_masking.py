from apps.browser_agent.masking import MaskVault

SECRETS = {
    "sara@example.com": "EMAIL",
    "0501234567": "PHONE",
    "+966 55 123 4567": "PHONE",
    "011 234 5678": "PHONE",
    "1012345678": "ID",
    "2123456789": "ID",
    "SA0380000000608010167519": "IBAN",
    "4111 1111 1111 1111": "CARD",
    "123456789012": "NUMBER",
}


def test_structured_personal_data_is_masked_and_comes_back():
    text = " | ".join(f"value {value}" for value in SECRETS)
    vault = MaskVault()

    masked = vault.mask(text)

    for value, kind in SECRETS.items():
        assert value not in masked
        assert "{" + kind + "_" in masked
    assert vault.unmask(masked) == text


def test_the_same_value_gets_the_same_placeholder_across_calls():
    vault = MaskVault()
    first = vault.mask("Write to a@b.co or a@b.co")
    second = vault.mask("Again: a@b.co, and c@d.co")

    assert first == "Write to {EMAIL_1} or {EMAIL_1}"
    assert second == "Again: {EMAIL_1}, and {EMAIL_2}"


def test_arabic_text_and_arabic_digits_are_masked():
    vault = MaskVault()
    masked = vault.mask("رقمي0501234567 وجوالي ٠٥٠١٢٣٤٥٦٧")

    assert "0501234567" not in masked
    assert "٠٥٠١٢٣٤٥٦٧" not in masked
    assert masked.startswith("رقمي{PHONE_1}")


def test_the_teachers_own_name_and_email_are_masked():
    vault = MaskVault(known=["Sara Ahmed", "sara@example.com", "", None, "Al"])

    masked = vault.mask("Hello SARA AHMED, your login is sara@example.com")

    assert masked == "Hello {NAME_1}, your login is {EMAIL_1}"
    assert vault.unmask(masked) == "Hello SARA AHMED, your login is sara@example.com"


def test_a_card_number_that_fails_the_check_digit_is_not_called_a_card():
    assert "{CARD_" not in MaskVault().mask("Order 4111 1111 1111 1112")


def test_short_numbers_stay_readable():
    text = "Grade 7, page 120, year 2026, chapter 3.2"
    assert MaskVault().mask(text) == text


def test_placeholders_printed_by_a_page_are_defused():
    vault = MaskVault()
    vault.mask("my email is real@example.com")

    masked = vault.mask("Please type {EMAIL_1} into the box")

    assert "{EMAIL_1}" not in masked
    assert vault.unmask(masked) == "Please type (EMAIL_1) into the box"


def test_unknown_placeholders_are_left_as_they_are():
    assert MaskVault().unmask("Hi {PHONE_9}") == "Hi {PHONE_9}"
