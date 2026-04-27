from __future__ import annotations

import re


class TextCleaner:
    """Normalizes extracted text and removes common navigation noise."""

    def __init__(self, *, min_line_length: int = 2) -> None:
        self.min_line_length = min_line_length
        # Exact single-word/short-phrase noise
        self._noise_lines = {
            "menu", "inicio", "home", "cerrar", "abrir",
            "facebook", "instagram", "linkedin", "youtube", "twitter", "x",
            "es", "en", "volver arriba", "sigue explorando...",
            "solicitar cita", "realizar pago", "ver directorio",
            "solicitar cita médica", "ver directorio de servicios",
            "comunícate por whatsapp", "te llamamos", "escríbenos",
            "especialidades", "directorio médico", "síguenos",
            "nuestra institución", "atención al paciente",
            "departamentos y servicios", "educación y docencia",
            "oficina internacional",
            "ingrese la palabra o palabras clave a buscar:",
            "conoce nuestra", "sarlaft",
            "-departamentos médicos", "-servicios",
        }
        # Patterns that indicate boilerplate/nav content
        self._noise_patterns = [
            re.compile(r"^©\s*copyright", re.IGNORECASE),
            re.compile(r"^resultados exámenes", re.IGNORECASE),
            re.compile(r"^radicación de factura", re.IGNORECASE),
            re.compile(r"^requerimientos legales", re.IGNORECASE),
            re.compile(r"^atención al usuario:", re.IGNORECASE),
            re.compile(r"^solicitud historia clínica:", re.IGNORECASE),
            re.compile(r"^departamento de comunicaciones:", re.IGNORECASE),
            re.compile(r"^\(\+57\)", re.IGNORECASE),
            re.compile(r"^[a-z_]+@fvl\.org\.co$", re.IGNORECASE),
            re.compile(r"^correo electrónico$", re.IGNORECASE),
            re.compile(r"^solicite información$", re.IGNORECASE),
            re.compile(r"^canales de contacto$", re.IGNORECASE),
            re.compile(r"^portafolio de servicios$", re.IGNORECASE),
            re.compile(r"^publicaciones y multimedia$", re.IGNORECASE),
            re.compile(r"^canal tv fvl$", re.IGNORECASE),
            re.compile(r"^directorio médico especialistas$", re.IGNORECASE),
            re.compile(r"^investigaciones clínicas$", re.IGNORECASE),
            re.compile(r"^pagos en línea$", re.IGNORECASE),
            re.compile(r"^trabaje con nosotros$", re.IGNORECASE),
            re.compile(r"^proveedores$", re.IGNORECASE),
            re.compile(r"^solicitar referenciación$", re.IGNORECASE),
            re.compile(r"^línea de transparencia$", re.IGNORECASE),
            re.compile(r"^la fundación$", re.IGNORECASE),
            re.compile(r"^información institucional$", re.IGNORECASE),
            re.compile(r"^educación universitaria$", re.IGNORECASE),
            re.compile(r"^alianza de usuarios", re.IGNORECASE),
            re.compile(r"^queremos conocer tu opinión$", re.IGNORECASE),
            re.compile(r"^comunícate con nosotros$", re.IGNORECASE),
        ]
        # Lines that are just navigation menu items (short, no verb, listing services)
        self._nav_menu_items = {
            "cardiología", "dermatología", "endocrinología", "gastroenterología",
            "geriatría", "hemato-oncología", "hematología", "hepatología",
            "infectología", "nefrología", "neumología", "neurología",
            "oncología", "psiquiatría", "radioterapia", "reumatología",
            "pediatría", "urología", "oftalmología", "mastología",
            "neurocirugía", "anestesiología", "electrofisiología",
            "fonoaudiología", "neuropsicología", "psicología",
            "hospitalización", "consulta externa", "endoscopia",
            "vacunación", "alergología", "trasplantes",
            "cuidados paliativos adultos", "cuidados paliativos pediátricos",
            "medicina del deporte", "medicina familiar", "medicina nuclear",
            "medicina nuclear molecular", "nutrición y dietética",
            "diagnóstico vascular", "telemedicina-liliconnect",
            "neurointervencionismo", "otorrinolaringología",
            "medicina interna", "medicina crítica", "imágenes diagnósticas",
            "patología y medicina de laboratorio", "materno infantil", "cirugía",
        }

    def clean(self, text: str | None) -> str:
        if not text:
            return ""

        normalized = text.replace("\r\n", "\n").replace("\r", "\n")

        # Try to extract content after known header boundary markers
        normalized = self._strip_header(normalized)
        # Try to strip footer content
        normalized = self._strip_footer(normalized)

        lines = [self._normalize_line(line) for line in normalized.split("\n")]

        cleaned_lines: list[str] = []
        seen_lines: set[str] = set()
        for line in lines:
            if not line:
                if cleaned_lines and cleaned_lines[-1] != "":
                    cleaned_lines.append("")
                continue

            if self._is_noise(line):
                continue

            line_key = line.casefold()
            if line_key in seen_lines:
                continue
            seen_lines.add(line_key)
            cleaned_lines.append(line)

        while cleaned_lines and cleaned_lines[-1] == "":
            cleaned_lines.pop()

        return "\n".join(cleaned_lines)

    @staticmethod
    def split_paragraphs(text: str) -> list[str]:
        return [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]

    def _is_noise(self, line: str) -> bool:
        lowered = line.casefold()
        if lowered in self._noise_lines:
            return True
        if lowered in self._nav_menu_items:
            return True
        if len(line) < self.min_line_length:
            return True
        for pattern in self._noise_patterns:
            if pattern.search(line):
                return True
        # Lines that are just "Cirugía de X" or "Clínica de X" nav items
        if re.match(r"^(cirugía|clínica|unidad|programa|laboratorio)\s+de\s+", lowered):
            if len(line) < 60:
                return True
        # Lines like "Data - Preparación para exámenes médicos"
        if lowered.startswith("data -"):
            return True
        return False

    @staticmethod
    def _strip_header(text: str) -> str:
        """Remove common header/nav content before main content."""
        # Look for patterns that indicate end of navigation
        markers = [
            '"Excelencia en salud al servicio de la comunidad"',
            "Volver a Acerca de Nosotros",
            "Sigue explorando...\n",
        ]
        best_pos = -1
        for marker in markers:
            pos = text.find(marker)
            if pos >= 0:
                end = pos + len(marker)
                # Skip to next line
                nl = text.find("\n", end)
                if nl >= 0:
                    best_pos = max(best_pos, nl + 1)
                else:
                    best_pos = max(best_pos, end)

        if best_pos > 0 and best_pos < len(text) * 0.8:
            return text[best_pos:]
        return text

    @staticmethod
    def _strip_footer(text: str) -> str:
        """Remove footer/contact boilerplate at end of page."""
        markers = [
            "Comunícate con nosotros\nSolicite Información",
            "Sigue explorando...",
            "© Copyright",
        ]
        best_pos = len(text)
        for marker in markers:
            pos = text.find(marker)
            if pos >= 0 and pos > len(text) * 0.3:
                best_pos = min(best_pos, pos)
        return text[:best_pos].rstrip()

    @staticmethod
    def _normalize_line(line: str) -> str:
        compact = re.sub(r"\s+", " ", line).strip()
        compact = compact.replace(" ,", ",").replace(" .", ".")
        return compact

