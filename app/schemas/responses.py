from pydantic import BaseModel, Field
from typing import Optional


class WriteDocumentResponse(BaseModel):
    """
    Schema para la respuesta exitosa de escritura en Google Docs.

    Attributes:
        success: Indica si la operación fue exitosa
        message: Mensaje descriptivo del resultado
        document_id: ID del documento modificado
        document_url: URL del documento de Google Docs
    """
    success: bool = Field(default=True, description="Estado de la operación")
    message: str = Field(..., description="Mensaje descriptivo")
    document_id: str = Field(..., description="ID del documento")
    document_url: str = Field(..., description="URL del documento de Google Docs")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Contenido escrito exitosamente en el documento",
                "document_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
                "document_url": "https://docs.google.com/document/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit"
            }
        }


class ErrorResponse(BaseModel):
    """
    Schema para respuestas de error.

    Attributes:
        success: Siempre False para errores
        error: Mensaje de error
        detail: Detalles adicionales del error (opcional)
    """
    success: bool = Field(default=False, description="Estado de la operación")
    error: str = Field(..., description="Mensaje de error")
    detail: Optional[str] = Field(None, description="Detalles adicionales del error")

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "Error al escribir en el documento",
                "detail": "El documento no existe o no tiene permisos"
            }
        }
