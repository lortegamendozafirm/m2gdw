# Markdown to Google Docs Writer

Microservicio FastAPI que convierte contenido Markdown generado por IA a formato nativo de Google Docs y lo escribe en documentos mediante una cuenta de servicio de Google Cloud.

## Características

- Conversión de Markdown a formato nativo de Google Docs
- Soporte para múltiples elementos de Markdown:
  - Encabezados (H1-H4)
  - Negrita, cursiva y código inline
  - Listas con viñetas y numeradas
  - Párrafos y saltos de línea
- Autenticación mediante cuenta de servicio de Google Cloud
- Validación de datos con Pydantic
- Arquitectura por capas (API, Service, Repository)
- API documentada automáticamente con OpenAPI/Swagger

## Arquitectura

```
writedocs/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── routes.py          # Endpoints de la API
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py              # Configuración de la aplicación
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── google_docs_repository.py  # Interacción con Google Docs API
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── requests.py            # Schemas de peticiones (Pydantic)
│   │   └── responses.py           # Schemas de respuestas (Pydantic)
│   ├── services/
│   │   ├── __init__.py
│   │   └── document_service.py    # Lógica de negocio
│   ├── utils/
│   │   ├── __init__.py
│   │   └── markdown_converter.py  # Conversión de Markdown
│   └── __init__.py
├── tests/                         # Tests (por implementar)
├── .env.example                   # Ejemplo de variables de entorno
├── .gitignore
├── main.py                        # Punto de entrada de la aplicación
├── requirements.txt               # Dependencias
└── README.md
```

### Capas de la aplicación

1. **API Layer** (`app/api/`): Endpoints HTTP, validación de entrada, manejo de errores HTTP
2. **Service Layer** (`app/services/`): Lógica de negocio, orquestación entre capas
3. **Repository Layer** (`app/repositories/`): Interacción con Google Docs API
4. **Utils** (`app/utils/`): Utilidades para conversión de Markdown
5. **Schemas** (`app/schemas/`): Modelos de datos con Pydantic

## Requisitos

- Python 3.8+
- Cuenta de servicio de Google Cloud con acceso a Google Docs API
- Archivo JSON de credenciales de la cuenta de servicio

## Instalación

1. Clonar el repositorio:
```bash
git clone <repository-url>
cd writedocs
```

2. Crear entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Configurar variables de entorno:
```bash
cp .env.example .env
```

Editar `.env` y configurar:
```env
GOOGLE_SERVICE_ACCOUNT_FILE=path/to/your/service-account-key.json
APP_NAME=Markdown to Google Docs Writer
APP_VERSION=1.0.0
DEBUG=False
```

## Configuración de Google Cloud

### 1. Crear una cuenta de servicio

1. Ir a [Google Cloud Console](https://console.cloud.google.com/)
2. Seleccionar o crear un proyecto
3. Ir a "IAM & Admin" > "Service Accounts"
4. Hacer clic en "Create Service Account"
5. Darle un nombre y descripción
6. No es necesario asignar roles específicos del proyecto
7. Hacer clic en "Done"

### 2. Crear clave de la cuenta de servicio

1. Hacer clic en la cuenta de servicio creada
2. Ir a la pestaña "Keys"
3. Hacer clic en "Add Key" > "Create new key"
4. Seleccionar formato JSON
5. Guardar el archivo JSON en un lugar seguro

### 3. Habilitar Google Docs API

1. Ir a "APIs & Services" > "Library"
2. Buscar "Google Docs API"
3. Hacer clic en "Enable"

### 4. Compartir el documento con la cuenta de servicio

1. Abrir el documento de Google Docs
2. Hacer clic en "Share"
3. Agregar el email de la cuenta de servicio (está en el archivo JSON como `client_email`)
4. Darle permisos de "Editor"

## Uso

### Iniciar el servidor

```bash
python main.py
```

O con uvicorn directamente:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

El servidor estará disponible en `http://localhost:8000`

### Documentación de la API

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Endpoints

#### POST /api/v1/write

Escribe contenido Markdown en un documento de Google Docs.

**Request:**
```json
{
  "markdown_content": "# Título\n\nEste es un **texto en negrita** y esto es *cursiva*.\n\n## Subtítulo\n\n- Item 1\n- Item 2",
  "document_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Contenido escrito exitosamente en el documento",
  "document_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
  "document_url": "https://docs.google.com/document/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit"
}
```

#### GET /api/v1/document/{document_id}

Obtiene información de un documento.

**Response:**
```json
{
  "document_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
  "title": "Mi Documento",
  "document_url": "https://docs.google.com/document/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit"
}
```

#### GET /api/v1/health

Health check del servicio.

**Response:**
```json
{
  "status": "healthy",
  "service": "Markdown to Google Docs Writer",
  "version": "1.0.0"
}
```

## Ejemplo con cURL

```bash
curl -X POST "http://localhost:8000/api/v1/write" \
  -H "Content-Type: application/json" \
  -d '{
    "markdown_content": "# Hola Mundo\n\nEste es un **ejemplo** de contenido *markdown*.\n\n## Lista de items\n\n- Item 1\n- Item 2\n- Item 3",
    "document_id": "TU_DOCUMENT_ID_AQUI"
  }'
```

## Ejemplo con Python

```python
import requests

url = "http://localhost:8000/api/v1/write"

payload = {
    "markdown_content": """# Título Principal

Este es un párrafo con **texto en negrita** y *texto en cursiva*.

## Subtítulo

- Primer item de lista
- Segundo item de lista
- Tercer item de lista

### Subsección

1. Primer item numerado
2. Segundo item numerado
3. Tercer item numerado

Código inline: `print("Hello World")`
""",
    "document_id": "TU_DOCUMENT_ID_AQUI"
}

response = requests.post(url, json=payload)
print(response.json())
```

## Elementos de Markdown soportados

- `# Heading 1` - Encabezado nivel 1
- `## Heading 2` - Encabezado nivel 2
- `### Heading 3` - Encabezado nivel 3
- `#### Heading 4` - Encabezado nivel 4
- `**bold**` - Texto en negrita
- `*italic*` - Texto en cursiva
- `***bold italic***` - Texto en negrita y cursiva
- `` `code` `` - Código inline
- `- item` o `* item` - Lista con viñetas
- `1. item` - Lista numerada

## Seguridad

- No incluyas el archivo JSON de credenciales en el repositorio
- Usa variables de entorno para configuración sensible
- En producción, configura CORS apropiadamente
- Implementa autenticación y autorización según necesidades

## Desarrollo

### Estructura de una petición

1. **API Layer**: Recibe la petición HTTP, valida con Pydantic
2. **Service Layer**: Coordina la lógica de negocio
3. **Utils**: Convierte Markdown a formato Google Docs
4. **Repository Layer**: Ejecuta operaciones en Google Docs API

### Agregar nuevos elementos de Markdown

Editar `app/utils/markdown_converter.py` y agregar lógica en el método `convert()`.

## Troubleshooting

### Error 403: Forbidden
- Verificar que la cuenta de servicio tiene acceso al documento
- Compartir el documento con el email de la cuenta de servicio

### Error 404: Not Found
- Verificar que el document_id es correcto
- El formato del ID debe ser: `1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms`

### Error al autenticar
- Verificar que el archivo JSON de credenciales existe
- Verificar que la ruta en `.env` es correcta
- Verificar que Google Docs API está habilitada en el proyecto

## Licencia

MIT

## Contribuciones

Las contribuciones son bienvenidas. Por favor, abre un issue o pull request.
