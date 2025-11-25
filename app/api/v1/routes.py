from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, Any
import logging

from app.schemas import WriteDocumentRequest, WriteDocumentResponse, ErrorResponse
from app.services import DocumentService
from app.repositories import GoogleDocsRepository
from app.core import settings

logger = logging.getLogger(__name__)

router = APIRouter()


def get_document_service() -> DocumentService:
    """
    Dependency injection para el servicio de documentos.

    Returns:
        Instancia de DocumentService
    """
    repository = GoogleDocsRepository(settings.GOOGLE_SERVICE_ACCOUNT_FILE)
    return DocumentService(repository)


@router.post(
    "/write",
    response_model=WriteDocumentResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Datos de entrada inválidos"},
        403: {"model": ErrorResponse, "description": "Sin permisos para el documento"},
        404: {"model": ErrorResponse, "description": "Documento no encontrado"},
        500: {"model": ErrorResponse, "description": "Error interno del servidor"}
    },
    summary="Escribir markdown en Google Docs",
    description="Convierte contenido Markdown a formato nativo de Google Docs y lo escribe en el documento especificado"
)
async def write_to_document(
    request: WriteDocumentRequest,
    service: DocumentService = Depends(get_document_service)
) -> WriteDocumentResponse:
    """
    Endpoint para escribir contenido Markdown en un documento de Google Docs.

    Args:
        request: Datos de la petición (markdown_content, document_id)
        service: Servicio de documentos (inyectado)

    Returns:
        Respuesta con información del resultado

    Raises:
        HTTPException: Si hay error en el proceso
    """
    try:
        logger.info(f"Recibida petición para documento: {request.document_id}")

        # Procesar la escritura
        result = service.write_markdown_to_document(request)

        return WriteDocumentResponse(
            success=result["success"],
            message=result["message"],
            document_id=result["document_id"],
            document_url=result["document_url"]
        )

    except ValueError as e:
        # Errores de validación o permisos
        error_message = str(e)
        logger.error(f"Error de validación: {error_message}")

        if "no existe" in error_message.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"success": False, "error": error_message}
            )
        elif "permisos" in error_message.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"success": False, "error": error_message}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "error": error_message}
            )

    except Exception as e:
        # Errores inesperados
        error_message = str(e)
        logger.error(f"Error inesperado: {error_message}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": "Error interno del servidor",
                "detail": error_message if settings.DEBUG else None
            }
        )


@router.get(
    "/document/{document_id}",
    summary="Obtener información del documento",
    description="Obtiene información básica de un documento de Google Docs"
)
async def get_document_info(
    document_id: str,
    service: DocumentService = Depends(get_document_service)
) -> Dict[str, Any]:
    """
    Endpoint para obtener información de un documento.

    Args:
        document_id: ID del documento
        service: Servicio de documentos (inyectado)

    Returns:
        Información del documento

    Raises:
        HTTPException: Si hay error al acceder al documento
    """
    try:
        logger.info(f"Obteniendo información del documento: {document_id}")
        result = service.get_document_info(document_id)
        return result

    except ValueError as e:
        error_message = str(e)
        logger.error(f"Error: {error_message}")

        if "no existe" in error_message.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"success": False, "error": error_message}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"success": False, "error": error_message}
            )

    except Exception as e:
        error_message = str(e)
        logger.error(f"Error inesperado: {error_message}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"success": False, "error": "Error interno del servidor"}
        )


@router.get(
    "/health",
    summary="Health check",
    description="Verifica el estado del servicio"
)
async def health_check() -> Dict[str, str]:
    """
    Endpoint de health check.

    Returns:
        Estado del servicio
    """
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION
    }
