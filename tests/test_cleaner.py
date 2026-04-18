from semantic_layer_fvl.processors import TextCleaner


def test_cleaner_removes_duplicate_and_noise_lines() -> None:
    raw_text = """
    Menu
    Quienes somos
    Quienes somos

    Fundacion Valle del Lili
    Fundacion Valle del Lili
    Historia institucional
    """

    cleaned = TextCleaner().clean(raw_text)

    assert "Menu" not in cleaned
    assert cleaned.count("Quienes somos") == 1
    assert cleaned.count("Fundacion Valle del Lili") == 1


def test_cleaner_removes_non_consecutive_duplicate_lines() -> None:
    """Navigation menus repeat across header, footer and sidebar — all repeats are dropped."""
    raw_text = """
    Cardiologia
    Descripcion del servicio de cardiologia.

    Servicios
    Cardiologia
    Neumologia
    """

    cleaned = TextCleaner().clean(raw_text)

    assert cleaned.count("Cardiologia") == 1
    assert "Neumologia" in cleaned


def test_cleaner_dedup_is_case_insensitive() -> None:
    raw_text = "Solicitar Cita\nsolicitar cita\nSOLICITAR CITA\n"
    cleaned = TextCleaner().clean(raw_text)
    assert cleaned.lower().count("solicitar cita") == 1
