import re
from typing import List, Dict, Any, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class MarkdownToGoogleDocsConverter:
    """
    Convierte contenido Markdown a formato nativo de Google Docs.
    Genera los requests necesarios para la API de Google Docs.
    """

    def __init__(self):
        self.current_index = 1  # Google Docs comienza en índice 1

    def convert(self, markdown_content: str, start_index: int = 1) -> List[Dict[str, Any]]:
        """
        Convierte contenido Markdown a requests de Google Docs API.
        """
        requests: List[Dict[str, Any]] = []
        self.current_index = start_index


        # Dividir el contenido en líneas
        lines = markdown_content.split("\n")

        for line in lines:
            # Línea vacía -> solo salto de línea explícito
            if not line.strip():
                req = self._create_insert_text_request("\n")
                if req:
                    requests.append(req)
                continue

            if line.startswith("# "):
                # Heading 1
                requests.extend(self._process_heading(line[2:], "HEADING_1"))
            elif line.startswith("## "):
                # Heading 2
                requests.extend(self._process_heading(line[3:], "HEADING_2"))
            elif line.startswith("### "):
                # Heading 3
                requests.extend(self._process_heading(line[4:], "HEADING_3"))
            elif line.startswith("#### "):
                # Heading 4
                requests.extend(self._process_heading(line[5:], "HEADING_4"))
            elif line.startswith("- ") or line.startswith("* "):
                # Lista con viñetas
                requests.extend(self._process_bullet_list(line[2:]))
            elif re.match(r"^\d+\. ", line):
                # Lista numerada
                match = re.match(r"^\d+\. (.*)", line)
                text_part = match.group(1) if match else ""
                requests.extend(self._process_numbered_list(text_part))
            else:
                # Texto normal con formato inline
                requests.extend(self._process_inline_formatting(line))

        logger.debug(f"Markdown convertido a {len(requests)} requests de Google Docs.")
        return requests

    # ---------------------------------------------------------
    # Helpers internos
    # ---------------------------------------------------------

    def _create_insert_text_request(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Crea un request para insertar texto.

        Args:
            text: Texto a insertar (no debe ser vacío)

        Returns:
            Request de inserción o None si text está vacío
        """
        if text is None:
            logger.debug("Saltando insertText con text=None")
            return None

        if text == "":
            # Aquí está el caso que rompe la API: lo evitamos
            logger.debug("Saltando insertText con text vacío ('').")
            return None

        request = {
            "insertText": {
                "location": {
                    "index": self.current_index,
                },
                "text": text,
            }
        }
        self.current_index += len(text)
        return request

    def _process_heading(self, text: str, heading_style: str) -> List[Dict[str, Any]]:
        """
        Procesa un encabezado.

        Args:
            text: Texto del encabezado
            heading_style: Estilo del encabezado (HEADING_1, HEADING_2, etc)

        Returns:
            Lista de requests
        """
        requests: List[Dict[str, Any]] = []
        start_index = self.current_index

        # Insertar texto del heading + salto de línea
        text_with_newline = (text or "") + "\n"
        insert_req = self._create_insert_text_request(text_with_newline)
        if insert_req:
            requests.append(insert_req)
        else:
            # Si no hay texto real, no intentamos aplicar estilo
            return requests

        # Aplicar estilo de encabezado
        requests.append(
            {
                "updateParagraphStyle": {
                    "range": {
                        "startIndex": start_index,
                        "endIndex": self.current_index - 1,
                    },
                    "paragraphStyle": {
                        "namedStyleType": heading_style,
                    },
                    "fields": "namedStyleType",
                }
            }
        )

        return requests

    def _process_bullet_list(self, text: str) -> List[Dict[str, Any]]:
        """
        Procesa un elemento de lista con viñetas.

        Args:
            text: Texto del elemento

        Returns:
            Lista de requests
        """
        requests: List[Dict[str, Any]] = []
        start_index = self.current_index

        # Insertar texto con formato inline
        text_requests, _ = self._parse_inline_formatting(text)
        requests.extend(text_requests)

        # Agregar salto de línea al final del ítem
        newline_req = self._create_insert_text_request("\n")
        if newline_req:
            requests.append(newline_req)

        # Crear lista con viñetas
        requests.append(
            {
                "createParagraphBullets": {
                    "range": {
                        "startIndex": start_index,
                        "endIndex": self.current_index - 1,
                    },
                    "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE",
                }
            }
        )

        return requests

    def _process_numbered_list(self, text: str) -> List[Dict[str, Any]]:
        """
        Procesa un elemento de lista numerada.

        Args:
            text: Texto del elemento

        Returns:
            Lista de requests
        """
        requests: List[Dict[str, Any]] = []
        start_index = self.current_index

        # Insertar texto con formato inline
        text_requests, _ = self._parse_inline_formatting(text)
        requests.extend(text_requests)

        # Salto de línea al final del ítem
        newline_req = self._create_insert_text_request("\n")
        if newline_req:
            requests.append(newline_req)

        # Crear lista numerada
        requests.append(
            {
                "createParagraphBullets": {
                    "range": {
                        "startIndex": start_index,
                        "endIndex": self.current_index - 1,
                    },
                    "bulletPreset": "NUMBERED_DECIMAL_ALPHA_ROMAN",
                }
            }
        )

        return requests

    def _process_inline_formatting(self, text: str) -> List[Dict[str, Any]]:
        """
        Procesa texto con formato inline (negrita, cursiva, etc).

        Args:
            text: Texto a procesar

        Returns:
            Lista de requests
        """
        requests, _ = self._parse_inline_formatting(text)

        # Agregar salto de línea al final del párrafo
        newline_req = self._create_insert_text_request("\n")
        if newline_req:
            requests.append(newline_req)

        return requests

    def _parse_inline_formatting(self, text: str) -> Tuple[List[Dict[str, Any]], int]:
        """
        Parsea y aplica formato inline (negrita, cursiva, código).

        Args:
            text: Texto a parsear

        Returns:
            Tupla con (lista de requests, longitud del texto insertado)
        """
        requests: List[Dict[str, Any]] = []
        total_length = 0

        # Patrones de formato inline
        # Orden importante: procesar *** antes de ** y * para evitar conflictos
        pattern = r"(\*\*\*.*?\*\*\*|\*\*.*?\*\*|\*.*?\*|`.*?`)"
        parts = re.split(pattern, text)

        for part in parts:
            if not part:
                continue

            # Negrita + cursiva
            if part.startswith("***") and part.endswith("***"):
                clean_text = part[3:-3]
                if not clean_text:
                    continue

                part_start = self.current_index
                insert_req = self._create_insert_text_request(clean_text)
                if insert_req:
                    requests.append(insert_req)
                    total_length += len(clean_text)

                    requests.append(
                        {
                            "updateTextStyle": {
                                "range": {
                                    "startIndex": part_start,
                                    "endIndex": self.current_index,
                                },
                                "textStyle": {"bold": True, "italic": True},
                                "fields": "bold,italic",
                            }
                        }
                    )

            # Negrita
            elif part.startswith("**") and part.endswith("**"):
                clean_text = part[2:-2]
                if not clean_text:
                    continue

                part_start = self.current_index
                insert_req = self._create_insert_text_request(clean_text)
                if insert_req:
                    requests.append(insert_req)
                    total_length += len(clean_text)

                    requests.append(
                        {
                            "updateTextStyle": {
                                "range": {
                                    "startIndex": part_start,
                                    "endIndex": self.current_index,
                                },
                                "textStyle": {"bold": True},
                                "fields": "bold",
                            }
                        }
                    )

            # Cursiva
            elif part.startswith("*") and part.endswith("*"):
                clean_text = part[1:-1]
                if not clean_text:
                    continue

                part_start = self.current_index
                insert_req = self._create_insert_text_request(clean_text)
                if insert_req:
                    requests.append(insert_req)
                    total_length += len(clean_text)

                    requests.append(
                        {
                            "updateTextStyle": {
                                "range": {
                                    "startIndex": part_start,
                                    "endIndex": self.current_index,
                                },
                                "textStyle": {"italic": True},
                                "fields": "italic",
                            }
                        }
                    )

            # Código inline
            elif part.startswith("`") and part.endswith("`"):
                clean_text = part[1:-1]
                if not clean_text:
                    continue

                part_start = self.current_index
                insert_req = self._create_insert_text_request(clean_text)
                if insert_req:
                    requests.append(insert_req)
                    total_length += len(clean_text)

                    requests.append(
                        {
                            "updateTextStyle": {
                                "range": {
                                    "startIndex": part_start,
                                    "endIndex": self.current_index,
                                },
                                "textStyle": {
                                    "weightedFontFamily": {
                                        "fontFamily": "Courier New"
                                    },
                                    "fontSize": {
                                        "magnitude": 10,
                                        "unit": "PT",
                                    },
                                },
                                "fields": "weightedFontFamily,fontSize",
                            }
                        }
                    )

            # Texto normal
            else:
                if part == "":
                    continue
                insert_req = self._create_insert_text_request(part)
                if insert_req:
                    requests.append(insert_req)
                    total_length += len(part)

        return requests, total_length
