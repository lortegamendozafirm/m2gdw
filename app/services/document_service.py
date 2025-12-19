# app/service/document_service.py
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
        self.repository = repository
        self.converter = MarkdownToGoogleDocsConverter()

    def write_markdown_to_document(self, request: WriteDocumentRequest) -> Dict[str, Any]:
            """
            Escribe el contenido Markdown procesando múltiples tablas y bloques de texto.
            """
            try:
                doc_id = request.document_id
                self.repository.clear_document(doc_id)
                
                blocks = self._parse_all_markdown_content(request.markdown_content)
                
                for block_type, content in blocks:
                    # Obtener el índice final JUSTO antes de insertar
                    end_index = self.repository.get_document_end_index(doc_id)
                    
                    if block_type == "text":
                        if content.strip():
                            reqs = self.converter.convert(content, start_index=end_index)
                            self.repository.write_content(doc_id, reqs)
                    
                    elif block_type == "table":
                        rows = len(content)
                        cols = len(content[0]) if rows > 0 else 0
                        
                        logger.info(f"Insertando tabla {rows}x{cols} en index={end_index}")
                        # 1. Insertar la tabla
                        self.repository.insert_table(doc_id, rows, cols, end_index)
                        self.repository.fill_table_at_index(doc_id, content, end_index)

                    
                return {
                    "success": True,
                    "message": "Contenido escrito exitosamente en el documento",
                    "document_url": self.repository.get_document_url(doc_id),
                    "document_id": doc_id
                }
            except Exception as e:
                logger.error(f"Error en write_markdown_to_document: {str(e)}")
                raise
            
    def _parse_all_markdown_content(self, markdown: str) -> List[Tuple[str, Any]]:
        """
        Analiza el Markdown completo y lo divide en una lista secuencial de bloques.
        Retorna: Lista de tuplas ('text', 'contenido') o ('table', [[fila1], [fila2]])
        """
        blocks = []
        lines = markdown.splitlines()
        current_text_block = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Identificar inicio de una tabla Markdown
            if "|" in line and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-{3,}[-\s|:]*\|?\s*$", lines[i+1]):
                # Si había texto acumulado, guardarlo primero
                if current_text_block:
                    blocks.append(("text", "\n".join(current_text_block)))
                    current_text_block = []
                
                # Extraer todas las líneas de la tabla
                table_lines = []
                while i < len(lines) and ("|" in lines[i] or re.match(r"^\s*\|?\s*:?-{3,}[-\s|:]*\|?\s*$", lines[i])):
                    # Solo procesar si la línea no está vacía
                    if lines[i].strip():
                        table_lines.append(lines[i])
                    i += 1
                
                # Convertir líneas de tabla a matriz de datos
                table_data = self._parse_table_lines(table_lines)
                if table_data:
                    blocks.append(("table", table_data))
                continue
            else:
                current_text_block.append(line)
                i += 1
        
        # Guardar el último bloque de texto si existe
        if current_text_block:
            blocks.append(("text", "\n".join(current_text_block)))
            
        return blocks

    def _parse_table_lines(self, table_lines: List[str]) -> List[List[str]]:
        """
        Convierte las líneas de una tabla Markdown en una matriz de strings.
        """
        data = []
        for idx, line in enumerate(table_lines):
            # Saltar la línea de separadores (---)
            if re.match(r"^\s*\|?\s*:?-{3,}[-\s|:]*\|?\s*$", line):
                continue
            
            # Limpiar bordes y dividir por pipe
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            data.append(cells)
        return data

    def get_document_info(self, document_id: str) -> Dict[str, Any]:
        """Obtiene información básica del documento."""
        try:
            document = self.repository.get_document(document_id)
            return {
                "document_id": document_id,
                "title": document.get('title', 'Sin título'),
                "document_url": self.repository.get_document_url(document_id)
            }
        except HttpError as e:
            logger.error(f"Error de Google API: {e.status_code}")
            raise