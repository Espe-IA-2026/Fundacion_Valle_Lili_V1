"""Tests unitarios offline para app_agent.tools.get_fvl_structured_info."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────


def _sample_data() -> dict:
    """Devuelve un dict de datos estructurados que replica la estructura real de fvl_info.json.

    Usa la misma jerarquía anidada del JSON de producción para garantizar que los
    tests validen el comportamiento real de _format_structured_data.
    """
    return {
        "informacion_corporativa": {
            "nombre_legal": "Fundación Valle del Lili",
            "nit": "890.303.394-7",
            "naturaleza_juridica": "Entidad privada sin ánimo de lucro",
            "pagina_web": "https://valledellili.org",
            "ranking_reputacion": "Mejor clínica de Colombia según América Economía.",
            "acreditaciones": [
                "Acreditación en Salud con Excelencia (MinSalud)",
                "Joint Commission International (JCI)",
            ],
        },
        "contactos_clave": {
            "central_telefonica": "+57 (2) 331 7000",
            "urgencias_directo": "+57 (2) 331 7001",
            "citas_medicas": "+57 (2) 331 9090",
            "whatsapp_citas": "+57 318 331 9090",
            "email_informacion": "info@valledellili.org",
        },
        "horarios_atencion": {
            "urgencias": "Atención 24 horas, 7 días a la semana",
            "consulta_externa": "Lunes a viernes 7:00 AM – 5:00 PM",
            "laboratorio_clinico": "Lunes a sábado 6:00 AM – 6:00 PM",
        },
        "sedes_y_ubicaciones": [
            {
                "nombre": "Sede Principal (Valle del Lili)",
                "direccion": "Carrera 98 # 18 - 49, Cali",
                "ciudad": "Cali",
                "servicios_principales": "Alta complejidad, Urgencias, Hospitalización.",
            },
            {
                "nombre": "Sede Limonar",
                "direccion": "Carrera 70 # 18 - 75, Cali",
                "ciudad": "Cali",
                "servicios_principales": "Consulta externa, Medicina física.",
            },
        ],
        "convenios_eps_y_aseguradoras": {
            "eps_regimen_contributivo": [
                "Sura EPS (Convenio integral)",
                "Sanitas EPS",
                "Compensar",
                "Nueva EPS (Alta complejidad)",
            ],
            "medicina_prepagada": [
                "Colmédica",
                "Medisanitas / Colsanitas",
                "Allianz",
            ],
            "aseguradoras_y_otros": [
                "SOAT (Atención inmediata por accidentes de tránsito)",
                "ARL (Sura, Positiva, Bolivar, etc.)",
            ],
            "nota_importante": (
                "Para EPS no listadas, la atención se centra en Urgencias Vitales "
                "o servicios específicos de alta complejidad previa autorización."
            ),
        },
        "servicios_destacados": ["Cardiología", "Trasplantes", "Oncología"],
        "servicios_de_apoyo": {
            "capilla": "Piso 1, Sede Principal. Misas: Lunes-Viernes 6:00 PM.",
            "parqueaderos": "Disponible en todas las sedes.",
        },
        "servicios_digitales": {
            "telemedicina": "Disponible vía App FVL Responde.",
        },
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
    """get_fvl_structured_info devuelve el NIT de la institución desde informacion_corporativa."""
    settings = _make_settings(tmp_path)

    with patch("app_agent.tools.get_settings", return_value=settings):
        from app_agent.tools import get_fvl_structured_info
        result = get_fvl_structured_info.invoke({"query": "¿Cuál es el NIT?"})

    assert "890.303.394-7" in result


def test_get_fvl_structured_info_incluye_telefono_central(tmp_path: Path) -> None:
    """get_fvl_structured_info devuelve el teléfono central de contacto desde contactos_clave."""
    settings = _make_settings(tmp_path)

    with patch("app_agent.tools.get_settings", return_value=settings):
        from app_agent.tools import get_fvl_structured_info
        result = get_fvl_structured_info.invoke({"query": "¿Cuál es el número de teléfono?"})

    assert "+57 (2) 331 7000" in result


def test_get_fvl_structured_info_incluye_horario_urgencias(tmp_path: Path) -> None:
    """get_fvl_structured_info devuelve el horario de urgencias desde horarios_atencion."""
    settings = _make_settings(tmp_path)

    with patch("app_agent.tools.get_settings", return_value=settings):
        from app_agent.tools import get_fvl_structured_info
        result = get_fvl_structured_info.invoke({"query": "¿Cuál es el horario de urgencias?"})

    assert "24 horas" in result


def test_get_fvl_structured_info_incluye_direccion_sede(tmp_path: Path) -> None:
    """get_fvl_structured_info incluye la dirección de la sede principal desde sedes_y_ubicaciones."""
    settings = _make_settings(tmp_path)

    with patch("app_agent.tools.get_settings", return_value=settings):
        from app_agent.tools import get_fvl_structured_info
        result = get_fvl_structured_info.invoke({"query": "¿Dónde están ubicadas las sedes?"})

    assert "Carrera 98" in result


def test_get_fvl_structured_info_incluye_acreditaciones(tmp_path: Path) -> None:
    """get_fvl_structured_info devuelve las acreditaciones desde informacion_corporativa."""
    settings = _make_settings(tmp_path)

    with patch("app_agent.tools.get_settings", return_value=settings):
        from app_agent.tools import get_fvl_structured_info
        result = get_fvl_structured_info.invoke({"query": "¿Qué acreditaciones tiene la FVL?"})

    assert "JCI" in result or "Joint Commission" in result


def test_get_fvl_structured_info_incluye_eps(tmp_path: Path) -> None:
    """get_fvl_structured_info devuelve las EPS en convenio desde convenios_eps_y_aseguradoras.

    Este es el caso de uso crítico: preguntas sobre cobertura de EPS deben responder
    con la lista de convenios del JSON estructurado, no con la base vectorial.
    """
    settings = _make_settings(tmp_path)

    with patch("app_agent.tools.get_settings", return_value=settings):
        from app_agent.tools import get_fvl_structured_info
        result = get_fvl_structured_info.invoke({"query": "¿Qué EPS tienen convenio?"})

    assert "CONVENIOS, EPS Y ASEGURADORAS" in result
    assert "Sura" in result
    assert "Sanitas" in result
    assert "Compensar" in result


def test_get_fvl_structured_info_incluye_medicina_prepagada(tmp_path: Path) -> None:
    """get_fvl_structured_info devuelve medicina prepagada desde convenios_eps_y_aseguradoras."""
    settings = _make_settings(tmp_path)

    with patch("app_agent.tools.get_settings", return_value=settings):
        from app_agent.tools import get_fvl_structured_info
        result = get_fvl_structured_info.invoke({"query": "¿Tienen convenio con medicina prepagada?"})

    assert "Colmédica" in result or "Medisanitas" in result


def test_get_fvl_structured_info_incluye_servicios_digitales(tmp_path: Path) -> None:
    """get_fvl_structured_info devuelve información sobre telemedicina desde servicios_digitales."""
    settings = _make_settings(tmp_path)

    with patch("app_agent.tools.get_settings", return_value=settings):
        from app_agent.tools import get_fvl_structured_info
        result = get_fvl_structured_info.invoke({"query": "¿Tienen telemedicina?"})

    assert "telemedicina" in result.lower() or "FVL Responde" in result


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
