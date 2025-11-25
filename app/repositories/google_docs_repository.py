# app/repositories/google_docs_repository.py
from typing import List, Dict, Any, Optional
import logging

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core import settings

logger = logging.getLogger(__name__)


class GoogleDocsRepository:
    """
    Repositorio para interactuar con Google Docs API.
    Maneja la autenticación y operaciones de escritura en documentos.
    """

    SCOPES = ["https://www.googleapis.com/auth/documents"]

    def __init__(self, service_account_file: Optional[str] = None) -> None:
        """
        Inicializa el repositorio con las credenciales de la cuenta de servicio.

        Args:
            service_account_file: Ruta al archivo JSON de credenciales.
                                  Si no se proporciona, se usa settings.GOOGLE_SERVICE_ACCOUNT_FILE.
        """
        # 👉 Prioridad: parámetro explícito > settings
        self.service_account_file = service_account_file or settings.GOOGLE_SERVICE_ACCOUNT_FILE

        if not self.service_account_file:
            msg = (
                "GOOGLE_SERVICE_ACCOUNT_FILE no está configurado. "
                "Configura la variable de entorno GOOGLE_SERVICE_ACCOUNT_FILE "
                "o pásala explícitamente al inicializar GoogleDocsRepository."
            )
            logger.error(msg)
            raise RuntimeError(msg)

        self.credentials = None
        self.service = None
        self._authenticate()

    def _authenticate(self) -> None:
        """Autentica usando la cuenta de servicio de Google Cloud."""
        try:
            self.credentials = service_account.Credentials.from_service_account_file(
                self.service_account_file,
                scopes=self.SCOPES,
            )
            # cache_discovery=False evita el warning del file_cache, pero es opcional
            self.service = build("docs", "v1", credentials=self.credentials, cache_discovery=False)
            logger.info("Autenticación exitosa con Google Docs API")
        except Exception as e:
            logger.error(f"Error en autenticación con Google Docs API: {e}")
            raise

    def get_document(self, document_id: str) -> Dict[str, Any]:
        """
        Obtiene información de un documento.

        Args:
            document_id: ID del documento de Google Docs

        Returns:
            Información del documento

        Raises:
            HttpError: Si hay error al acceder al documento
        """
        try:
            document = self.service.documents().get(documentId=document_id).execute()
            logger.info(f"Documento obtenido: {document_id}")
            return document
        except HttpError as error:
            logger.error(f"Error al obtener documento {document_id}: {error}")
            raise

    def write_content(self, document_id: str, requests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Escribe contenido en un documento usando batch update.

        Args:
            document_id: ID del documento de Google Docs
            requests: Lista de requests de la API de Google Docs

        Returns:
            Respuesta de la API

        Raises:
            HttpError: Si hay error al escribir en el documento
        """
        cleaned_requests: List[Dict[str, Any]] = []
        skipped_count = 0

        for i, req in enumerate(requests):
            insert = req.get("insertText")
            if insert is not None:
                text = insert.get("text")

                # Caso 1: no existe la clave "text"
                if "text" not in insert:
                    logger.warning(
                        f"[SANITIZE] insertText sin clave 'text' en requests[{i}], "
                        f"request original: {req}"
                    )
                    skipped_count += 1
                    continue

                # Caso 2: text es None o cadena vacía
                if text is None or text == "":
                    logger.warning(
                        f"[SANITIZE] insertText con texto vacío en requests[{i}], "
                        f"request original: {req}"
                    )
                    skipped_count += 1
                    continue

            cleaned_requests.append(req)

        logger.info(
            f"Preparando escritura en documento {document_id}: "
            f"{len(cleaned_requests)} requests válidas, "
            f"{skipped_count} requests insertText vacías ignoradas."
        )

        if not cleaned_requests:
            logger.warning(
                f"No hay requests válidas para escribir en documento {document_id}. "
                f"Se omite el batchUpdate."
            )
            return {"message": "No hay contenido válido para escribir"}

        try:
            result = (
                self.service.documents()
                .batchUpdate(
                    documentId=document_id,
                    body={"requests": cleaned_requests},
                )
                .execute()
            )
            logger.info(f"Contenido escrito en documento: {document_id}")
            return result
        except HttpError as error:
            logger.error(f"Error al escribir en documento {document_id}: {error}")
            raise

    def clear_document(self, document_id: str) -> Dict[str, Any]:
        """
        Limpia todo el contenido del documento.
        """
        try:
            document = self.get_document(document_id)
            body = document.get("body", {})
            content = body.get("content", [])

            if not content:
                logger.info(f"Documento {document_id} sin contenido (body.content vacío)")
                return {"message": "El documento ya está vacío"}

            max_end_index = 1
            for el in content:
                if "endIndex" in el:
                    max_end_index = max(max_end_index, el["endIndex"])

            start_index = 1
            end_index = max_end_index - 1

            if end_index <= start_index:
                logger.info(
                    f"No hay contenido real para limpiar en documento {document_id} "
                    f"(startIndex={start_index}, endIndex={end_index}, max_end_index={max_end_index})"
                )
                return {"message": "El documento ya está vacío o solo contiene el carácter final"}

            logger.debug(
                f"Limpiando documento {document_id} con rango startIndex={start_index}, "
                f"endIndex={end_index}"
            )

            requests = [
                {
                    "deleteContentRange": {
                        "range": {
                            "startIndex": start_index,
                            "endIndex": end_index,
                        }
                    }
                }
            ]

            result = (
                self.service.documents()
                .batchUpdate(documentId=document_id, body={"requests": requests})
                .execute()
            )
            logger.info(f"Documento limpiado: {document_id}")
            return result

        except HttpError as error:
            logger.error(f"Error al limpiar documento {document_id}: {error}")
            raise

    def get_document_url(self, document_id: str) -> str:
        """Genera la URL del documento de Google Docs."""
        return f"https://docs.google.com/document/d/{document_id}/edit"

    def insert_table(self, document_id: str, rows: int, cols: int, location_index: int) -> Dict[str, Any]:
        """
        Inserta una tabla nativa de Google Docs en la posición indicada.
        """
        requests = [
            {
                "insertTable": {
                    "rows": rows,
                    "columns": cols,
                    "location": {"index": location_index},
                }
            }
        ]

        result = (
            self.service.documents()
            .batchUpdate(documentId=document_id, body={"requests": requests})
            .execute()
        )
        logger.info(f"Tabla {rows}x{cols} insertada en documento {document_id} en index={location_index}")
        return result

    def fill_first_table(self, document_id: str, data: List[List[str]]) -> Dict[str, Any]:
        """
        Rellena la primera tabla del documento con los valores de data (filas x columnas).
        Inserta el texto de las celdas en orden inverso para no romper los índices.
        """
        doc = self.get_document(document_id)
        content = doc.get("body", {}).get("content", [])

        table = None
        for element in content:
            if "table" in element:
                table = element["table"]
                break

        if table is None:
            raise ValueError("No se encontró una tabla en el documento para rellenar.")

        cell_positions = []  # (start_index, row_idx, col_idx)
        for i, row in enumerate(table.get("tableRows", [])):
            for j, cell in enumerate(row.get("tableCells", [])):
                cell_content = cell.get("content", [])
                if not cell_content:
                    continue

                first_paragraph = cell_content[0].get("paragraph", {})
                elements = first_paragraph.get("elements", [])
                if not elements:
                    continue

                start_index = elements[0].get("startIndex")
                if start_index is None:
                    continue

                cell_positions.append((start_index, i, j))

        if not cell_positions:
            logger.warning("No se encontraron posiciones válidas para celdas de tabla.")
            return {"message": "No se pudo rellenar la tabla"}

        cell_positions.sort(key=lambda x: x[0], reverse=True)

        requests: List[Dict[str, Any]] = []

        for start_index, i, j in cell_positions:
            if i >= len(data) or j >= len(data[i]):
                continue

            text = data[i][j]
            if not text:
                continue

            requests.append(
                {
                    "insertText": {
                        "location": {"index": start_index},
                        "text": text,
                    }
                }
            )

        if not requests:
            logger.warning("No se generaron requests para rellenar la tabla.")
            return {"message": "No hay contenido válido para escribir en la tabla."}

        result = (
            self.service.documents()
            .batchUpdate(documentId=document_id, body={"requests": requests})
            .execute()
        )
        logger.info(f"Tabla del documento {document_id} rellenada correctamente.")
        return result

    def get_document_end_index(self, document_id: str) -> int:
        """
        Devuelve el endIndex máximo del documento (para insertar contenido al final).
        """
        doc = self.get_document(document_id)
        content = doc.get("body", {}).get("content", [])
        max_end = 1
        for el in content:
            if "endIndex" in el:
                max_end = max(max_end, el["endIndex"])
        return max_end - 1  # evitamos incluir el newline final
