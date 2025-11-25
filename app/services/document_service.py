# app/services/document_service.py
from typing import Dict, Any, Tuple, List, Optional
import re
from googleapiclient.errors import HttpError
import logging

from app.repositories import GoogleDocsRepository
from app.utils import MarkdownToGoogleDocsConverter
from app.schemas import WriteDocumentRequest

logger = logging.getLogger(__name__)


class DocumentService:
    """
    Servicio que contiene la lógica de negocio para escribir en Google Docs.
    Coordina entre el conversor de Markdown y el repositorio de Google Docs.
    """

    def __init__(self, repository: GoogleDocsRepository):
        """
        Inicializa el servicio.

        Args:
            repository: Repositorio de Google Docs
        """
        self.repository = repository
        self.converter = MarkdownToGoogleDocsConverter()

    def write_markdown_to_document(
        self,
        request: WriteDocumentRequest
    ) -> Dict[str, Any]:

        try:
            doc_id = request.document_id

            # Validar que el documento existe y tenemos acceso
            logger.info(f"Validando acceso al documento: {doc_id}")
            _ = self.repository.get_document(doc_id)

            # Limpiar el contenido existente del documento
            logger.info(f"Limpiando contenido del documento: {doc_id}")
            self.repository.clear_document(doc_id)

            # --- Nuevo: detectar tabla en el markdown ---
            before_md, table_data, after_md = self._split_markdown_and_first_table(
                request.markdown_content
            )

            # Caso 1: NO hay tabla -> comportamiento de siempre
            if table_data is None:
                logger.info("Markdown sin tabla, usando flujo estándar.")
                google_docs_requests = self.converter.convert(before_md, start_index=1)
                logger.info(f"Escribiendo contenido en documento: {doc_id}")
                result = self.repository.write_content(doc_id, google_docs_requests)

            else:
                logger.info(
                    f"Se detectó una tabla Markdown con "
                    f"{len(table_data)} filas y {len(table_data[0]) if table_data else 0} columnas."
                )

                # 1) Texto antes de la tabla
                if before_md.strip():
                    logger.info("Escribiendo texto antes de la tabla...")
                    reqs_before = self.converter.convert(before_md, start_index=1)
                    self.repository.write_content(doc_id, reqs_before)

                # 2) Insertar tabla nativa al final del contenido actual
                end_index = self.repository.get_document_end_index(doc_id)
                rows = len(table_data)
                cols = len(table_data[0]) if rows > 0 else 0
                logger.info(
                    f"Inserción de tabla nativa {rows}x{cols} en index={end_index}..."
                )
                self.repository.insert_table(doc_id, rows=rows, cols=cols, location_index=end_index)

                # 3) Rellenar la tabla
                self.repository.fill_first_table(doc_id, table_data)

                # 4) Texto después de la tabla
                if after_md.strip():
                    logger.info("Escribiendo texto después de la tabla...")
                    # Recalcular índice final después de la tabla
                    new_end_index = self.repository.get_document_end_index(doc_id)
                    reqs_after = self.converter.convert(after_md, start_index=new_end_index)
                    self.repository.write_content(doc_id, reqs_after)

                # Para mantener contrato, devolvemos el último resultado de escritura
                result = {"message": "Texto + tabla escritos correctamente"}

            # Generar URL del documento
            document_url = self.repository.get_document_url(doc_id)

            logger.info(f"Escritura exitosa en documento: {doc_id}")

            return {
                "success": True,
                "message": "Contenido escrito exitosamente en el documento",
                "document_id": doc_id,
                "document_url": document_url,
                "result": result,
            }

        except HttpError as e:
            error_message = f"Error de Google API: {e.status_code} - {e.error_details}"
            logger.error(error_message)

            if e.status_code == 404:
                raise ValueError("El documento no existe")
            elif e.status_code == 403:
                raise ValueError(
                    "No hay permisos para acceder al documento. "
                    "Verifica que la cuenta de servicio tenga acceso."
                )
            else:
                raise Exception(error_message)

        except Exception as e:
            logger.error(f"Error inesperado: {str(e)}")
            raise Exception(f"Error al procesar la solicitud: {str(e)}")


    def get_document_info(self, document_id: str) -> Dict[str, Any]:
        """
        Obtiene información de un documento.

        Args:
            document_id: ID del documento

        Returns:
            Información del documento

        Raises:
            ValueError: Si el documento no existe o no hay permisos
        """
        try:
            document = self.repository.get_document(document_id)
            return {
                "document_id": document_id,
                "title": document.get('title', 'Sin título'),
                "document_url": self.repository.get_document_url(document_id)
            }
        except HttpError as e:
            if e.status_code == 404:
                raise ValueError("El documento no existe")
            elif e.status_code == 403:
                raise ValueError("No hay permisos para acceder al documento")
            else:
                raise Exception(f"Error al obtener información del documento: {str(e)}")
    # ---------- Helpers internos para tablas en Markdown ----------

    def _split_markdown_and_first_table(
        self, markdown: str
    ) -> Tuple[str, Optional[List[List[str]]], str]:
        """
        Busca la primera tabla estilo Markdown y separa:
        - texto antes
        - datos de la tabla (matriz filas x columnas)
        - texto después

        Si no encuentra tabla, devuelve (markdown, None, "").
        """
        lines = markdown.splitlines()
        start = end = None

        for i, line in enumerate(lines):
            # Buscamos una línea con '|' que NO sea solo separadores
            if "|" in line and not re.match(r"^\s*\|?\s*-[-\s|:]*\|?\s*$", line):
                # Verificamos que la siguiente línea tenga separadores ---|---|---
                if (
                    i + 1 < len(lines)
                    and re.match(r"^\s*\|?\s*:?-{3,}[-\s|:]*\|?\s*$", lines[i + 1])
                ):
                    start = i
                    j = i + 2
                    # Avanzar mientras haya filas con '|'
                    while j < len(lines) and "|" in lines[j] and lines[j].strip():
                        j += 1
                    end = j
                    break

        if start is None or end is None:
            # No hay tabla
            return markdown, None, ""

        table_lines = lines[start:end]
        before = "\n".join(lines[:start])
        after = "\n".join(lines[end:])

        # Parsear líneas de tabla a matriz
        data: List[List[str]] = []
        for idx, line in enumerate(table_lines):
            # Saltar fila de separadores (la segunda)
            if idx == 1 and re.match(r"^\s*\|?\s*:?-{3,}[-\s|:]*\|?\s*$", line):
                continue
            stripped = line.strip().strip("|")
            cells = [c.strip() for c in stripped.split("|")]
            data.append(cells)

        return before, data, after
