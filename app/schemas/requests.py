from pydantic import BaseModel, Field, field_validator, ConfigDict


class WriteDocumentRequest(BaseModel):
    """
    Schema para la petición de escritura en Google Docs.

    Attributes:
        markdown_content: Contenido en formato Markdown a escribir
        document_id: ID del documento de Google Docs
    """

    markdown_content: str = Field(
        ...,
        description="Contenido en formato Markdown generado por IA",
        min_length=1,
        max_length=1_000_000,
    )

    document_id: str = Field(
        ...,
        description="ID del documento de Google Docs",
        pattern=r"^[a-zA-Z0-9-_]+$",
        min_length=10,
    )

    # ✅ Pydantic v2: usar field_validator en lugar de validator
    @field_validator("markdown_content")
    @classmethod
    def validate_markdown_content(cls, v: str) -> str:
        """Valida que el contenido markdown no esté vacío después de strip"""
        if not v.strip():
            raise ValueError("El contenido markdown no puede estar vacío")
        return v.strip()

    @field_validator("document_id")
    @classmethod
    def validate_document_id(cls, v: str) -> str:
        """Valida el formato del ID del documento"""
        if not v.strip():
            raise ValueError("El ID del documento no puede estar vacío")
        return v.strip()

    # ✅ Pydantic v2: usar model_config en lugar de class Config
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "markdown_content": (
                    "# Título\n\nEste es un **texto en negrita** y esto es *cursiva*."
                    "\n\n## Subtítulo\n\n- Item 1\n- Item 2"
                ),
                "document_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
            }
        }
    )
