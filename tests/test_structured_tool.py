"""Tests unitarios offline para app_agent.tools.get_fvl_structured_info."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────


def _sample_data() -> dict:
    """Devuelve un dict de datos estructurados mínimo para los tests."""
    return {
        "razon_social": "Fundación Valle del Lili",
        "nit": "890.303.394-7",
        "año_fundacion": 1992,
        "tipo_entidad": "IPS sin ánimo de lucro",
        "director_medico": "Dr. Carlos Enrique Arango Aguirre",
        "director_ejecutivo": "Dr. Juan Guillermo Ortiz Arboleda",
        "sitio_web": "https://www.valledellili.org",
        "contactos": {
            "central": "+57 (2) 331 7000",
            "urgencias": "+57 (2) 331 7001",
            "citas": "+57 (2) 331 7007",
        },
        "horarios": {
            "urgencias": "24 horas al día, 7 días a la semana",
            "consulta_externa": "Lunes a viernes 7:00–17:00",
        },
        "sedes": [
            {
                "nombre": "Sede Principal",
                "direccion": "Cl. 98 #18-49, Cali",
                "telefono": "+57 (2) 331 7000",
                "referencia": "Ciudad Jardín",
            }
        ],
        "servicios_destacados": ["Cardiología", "Trasplantes", "Oncología"],
        "acreditaciones": ["Joint Commission International (JCI)"],
        "redes_sociales": {
            "facebook": "https://www.facebook.com/FundacionValledelLili",
            "instagram": "@fundacionvalledellili",
        },
        "metodos_pago": {
            "modalidades": ["EPS en convenio", "Particular"],
            "horario_caja": "Lunes a viernes 7:00–16:00",
        },
        "donaciones": {
            "descripcion": "Entidad sin ánimo de lucro.",
            "contacto": "donaciones@valledellili.org",
        },
        "preguntas_frecuentes": [
            {
                "pregunta": "¿Cuál es el NIT de la Fundación?",
                "respuesta": "El NIT es 890.303.394-7.",
            }
        ],
    }


def _make_settings(tmp_path: Path, data: dict | None = None) -> MagicMock:
    """Crea un Settings mock con un archivo JSON de prueba en tmp_path."""
    settings = MagicMock()
    data_file = tmp_path / "fvl_info.json"
    data_file.write_text(
        json.dumps(data if data is not None else _sample_data(), ensure_ascii=False),
        encoding="utf-8",
    )
    settings.resolved_structured_data_path = data_file
    return settings


# ── Tests de metadatos de la tool ─────────────────────────────────────────────


def test_get_fvl_structured_info_es_langchain_tool() -> None:
    """get_fvl_structured_info expone el contrato de herramienta LangChain.

    Verifica nombre y descripción que el agente usa para decidir cuándo invocarla.
    """
    from app_agent.tools import get_fvl_structured_info

    assert get_fvl_structured_info.name == "get_fvl_structured_info"
    assert len(get_fvl_structured_info.description) > 20
    assert "FVL" in get_fvl_structured_info.description or "Fundación" in get_fvl_structured_info.description


# ── Tests de datos devueltos ──────────────────────────────────────────────────


def test_get_fvl_structured_info_incluye_nit(tmp_path: Path) -> None:
    """get_fvl_structured_info devuelve el NIT de la institución."""
    settings = _make_settings(tmp_path)

    with patch("app_agent.tools.get_settings", return_value=settings):
        from app_agent.tools import get_fvl_structured_info
        result = get_fvl_structured_info.invoke({"query": "¿Cuál es el NIT?"})

    assert "890.303.394-7" in result


def test_get_fvl_structured_info_incluye_telefono_central(tmp_path: Path) -> None:
    """get_fvl_structured_info devuelve el teléfono central de contacto."""
    settings = _make_settings(tmp_path)

    with patch("app_agent.tools.get_settings", return_value=settings):
        from app_agent.tools import get_fvl_structured_info
        result = get_fvl_structured_info.invoke({"query": "¿Cuál es el número de teléfono?"})

    assert "+57 (2) 331 7000" in result


def test_get_fvl_structured_info_incluye_horario_urgencias(tmp_path: Path) -> None:
    """get_fvl_structured_info devuelve el horario de urgencias."""
    settings = _make_settings(tmp_path)

    with patch("app_agent.tools.get_settings", return_value=settings):
        from app_agent.tools import get_fvl_structured_info
        result = get_fvl_structured_info.invoke({"query": "¿Cuál es el horario de urgencias?"})

    assert "24 horas" in result


def test_get_fvl_structured_info_incluye_direccion_sede(tmp_path: Path) -> None:
    """get_fvl_structured_info incluye la dirección de la sede principal."""
    settings = _make_settings(tmp_path)

    with patch("app_agent.tools.get_settings", return_value=settings):
        from app_agent.tools import get_fvl_structured_info
        result = get_fvl_structured_info.invoke({"query": "¿Dónde están ubicadas las sedes?"})

    assert "Cl. 98 #18-49" in result


def test_get_fvl_structured_info_incluye_director(tmp_path: Path) -> None:
    """get_fvl_structured_info devuelve el nombre del director médico."""
    settings = _make_settings(tmp_path)

    with patch("app_agent.tools.get_settings", return_value=settings):
        from app_agent.tools import get_fvl_structured_info
        result = get_fvl_structured_info.invoke({"query": "¿Quién es el director?"})

    assert "Arango Aguirre" in result


def test_get_fvl_structured_info_incluye_redes_sociales(tmp_path: Path) -> None:
    """get_fvl_structured_info incluye las redes sociales de la FVL."""
    settings = _make_settings(tmp_path)

    with patch("app_agent.tools.get_settings", return_value=settings):
        from app_agent.tools import get_fvl_structured_info
        result = get_fvl_structured_info.invoke({"query": "¿Cuáles son las redes sociales?"})

    assert "facebook" in result.lower() or "instagram" in result.lower()


def test_get_fvl_structured_info_incluye_preguntas_frecuentes(tmp_path: Path) -> None:
    """get_fvl_structured_info incluye la sección de preguntas frecuentes."""
    settings = _make_settings(tmp_path)

    with patch("app_agent.tools.get_settings", return_value=settings):
        from app_agent.tools import get_fvl_structured_info
        result = get_fvl_structured_info.invoke({"query": "preguntas frecuentes"})

    assert "PREGUNTAS FRECUENTES" in result


# ── Tests de manejo de errores ────────────────────────────────────────────────


def test_get_fvl_structured_info_archivo_no_encontrado() -> None:
    """get_fvl_structured_info devuelve mensaje de error si el archivo JSON no existe."""
    settings = MagicMock()
    settings.resolved_structured_data_path = Path("/no/existe/fvl_info.json")

    with patch("app_agent.tools.get_settings", return_value=settings):
        from app_agent.tools import get_fvl_structured_info
        result = get_fvl_structured_info.invoke({"query": "teléfono"})

    assert "No se encontró" in result


def test_get_fvl_structured_info_json_malformado(tmp_path: Path) -> None:
    """get_fvl_structured_info devuelve mensaje de error si el JSON está malformado."""
    bad_file = tmp_path / "fvl_info.json"
    bad_file.write_text("{esto no es json válido}", encoding="utf-8")
    settings = MagicMock()
    settings.resolved_structured_data_path = bad_file

    with patch("app_agent.tools.get_settings", return_value=settings):
        from app_agent.tools import get_fvl_structured_info
        result = get_fvl_structured_info.invoke({"query": "teléfono"})

    assert "Error al leer" in result
