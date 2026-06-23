[![RU](https://img.shields.io/badge/lang-ru-red.svg)](README.ru.md)  [![EN](https://img.shields.io/badge/lang-en-green.svg)](README.md)

# Provision.scan — OCR Document Recognition Service

C++ implementation of an OCR and document recognition service. Fully compatible with the original Python/aiohttp
version.

---

## Table of Contents

- [Installation and Launch](#installation-and-launch)
    - [Windows](#windows)
    - [Linux](#linux)
    - [Docker](#docker)
- [API Endpoints](#api-endpoints)
    - [Health](#health)
    - [Reload Models](#reload-models)
    - [Document Recognition (processing)](#document-recognition-processing)
    - [Document Recognition (processing2)](#document-recognition-processing2)
- [Document Templates](#document-templates)
- [Input Formats](#input-formats)
- [Response Format](#response-format)
- [Code Examples](#code-examples)

---

## Installation and Launch

### Windows

### `Installation`

1. Download the [installer](https://provlabs.tech/downloads/provision_ocr_trial_setup.exe)
2. Run `provision_ocr_trial.exe`
3. In the window that opens, select the language and installation path
4. Click `Install`

### `Launch`

1. In the console window that opens, wait for the status `Provision Scan: READY`
2. The `Listening on` field will show the API URL
3. From the folder where OCR is installed, run `ProvisionOCR.exe`

### Linux

`In development`

### Docker

1. Pull the Docker image:

```bash
docker pull registry.provlabs.tech/hub/trial/provision_ocr:latest
```

2. Run the container:

**CMD / bash:**

```bash
docker run -d --name provision_ocr --gpus all -p 8098:8098 --restart always registry.provlabs.tech/hub/trial/provision_ocr:latest
```

**PowerShell:**

```powershell
docker run -d `
  --name provision_ocr `
  --gpus all `
  -p 8098:8098 `
  --restart always `
  registry.provlabs.tech/hub/trial/provision_ocr:latest
```

> `--gpus all` flag enables GPU usage. To run on CPU or macOS, omit this flag.

3. Verify the container is running:

```bash
docker ps
```

After a successful start, the service is available at:

- API:          `http://localhost:8098/`
- Swagger UI:   `http://localhost:8098/docs`
- Health check: `http://localhost:8098/health`

4. Stop the container:

```bash
docker stop provision_ocr
```

---

## API Endpoints

### Health

```
POST /health
```

Service availability check (liveness probe).

**Responses:**

| Code  | Description                                      |
|-------|--------------------------------------------------|
| `200` | Service is running normally                      |
| `503` | Service temporarily unavailable (middleware off) |

**Example response (200):**

```json
{
  "status": "ok"
}
```

---

### Reload Models

```
POST /reload_service
```

Unloads and reloads all ONNX models on the next request: Mask R-CNN, CRAFT, TextRecognizer, CharRecognizer,
EfficientNet, Edge. Useful after replacing weights on disk without restarting the service.

**Responses:**

| Code  | Description     |
|-------|-----------------|
| `200` | Reload accepted |

**Example response (200):**

```json
{
  "status": "ok"
}
```

---

### Document Recognition (processing)

```
POST /processing/{template}
```

Main recognition endpoint. Accepts images both as raw binary and via multipart/form-data.

**Path parameters:**

| Parameter  | Type   | Description                                                       |
|------------|--------|-------------------------------------------------------------------|
| `template` | string | Document template (see [Document Templates](#document-templates)) |

**Request body:** image as raw binary or multipart with field `body` / `file`.

**Responses:**

| Code  | Description                                                        |
|-------|--------------------------------------------------------------------|
| `200` | Recognition result                                                 |
| `400` | Bad request (missing file field, unknown template, pipeline error) |
| `415` | Unsupported image format                                           |

---

### Document Recognition (processing2)

```
POST /processing2/{template}
```

**Parameters:** same as `/processing/{template}`.

---

## Document Templates

| Template    | Description                 | data               | Supported formats  |
|-------------|-----------------------------|--------------------|--------------------|
| `passport`  | Russian Federation passport | paragraphs         | image, scanned-pdf |
| `snils`     | SNILS (pension certificate) | paragraphs         | image, scanned-pdf |
| `agreement` | Contract / Agreement        | paragraphs, tables | image, scanned-pdf |
| `default`   | Universal template          | blocks, tables     | image, pdf(all)    |

---

## Input Formats

The service accepts images in the following formats:

| MIME type             | Format                                         |
|-----------------------|------------------------------------------------|
| `image/jpeg`          | JPEG                                           |
| `image/png`           | PNG                                            |
| `image/bmp`           | BMP                                            |
| `image/tiff`          | TIFF                                           |
| `image/gif`           | GIF (static)                                   |
| `image/webp`          | WEBP                                           |
| `image/png`           | PDF (the service will detect it automatically) |
| `multipart/form-data` | Field `file` or `body` containing the image    |

---

## Response Format

### Top-level structure

```json
{
  "documents": [
    {
      "width": 715,
      "height": 999,
      "schema_version": 1,
      "pages": []
    }
  ]
}
```

| Field            | Type  | Description                  |
|------------------|-------|------------------------------|
| `width`          | int   | Image width in pixels        |
| `height`         | int   | Image height in pixels       |
| `schema_version` | int   | Response format version      |
| `pages`          | array | Document pages (usually 1–2) |

---

### `Page` object

```json
{
  "page_number": 1,
  "loc": {
    "x1": 0,
    "y1": 0,
    "x2": 715,
    "y2": 999
  },
  "blocks": [],
  "paragraphs": [],
  "tables": [],
  "figures": []
}
```

| Field         | Type   | Description                                                           |
|---------------|--------|-----------------------------------------------------------------------|
| `page_number` | int    | Page number (starting from 1)                                         |
| `loc`         | object | Page bounding box in pixels                                           |
| `blocks`      | array  | Flat list of all recognized blocks on the page                        |
| `paragraphs`  | array  | Grouped blocks; for template documents — the primary source of fields |
| `tables`      | array  | Recognized tables (empty for passport/SNILS templates)                |
| `figures`     | array  | Detected figures/images                                               |

---

### `Block` object

Found in `page.blocks`, `paragraph.blocks`, and `table.cells[r][c].blocks`.

```json
{
  "text": "IVANOV",
  "tag": "lastName",
  "prob": 1.0,
  "loc": {
    "x1": 328,
    "y1": 515,
    "x2": 422,
    "y2": 528
  }
}
```

| Field  | Type   | Description                                                             |
|--------|--------|-------------------------------------------------------------------------|
| `text` | string | Recognized text of the block                                            |
| `tag`  | string | Semantic tag (e.g., `lastName`, `dateIssued`, `word`, `header`, `data`) |
| `prob` | float  | Recognition confidence (0–1)                                            |
| `loc`  | object | Block bounding box: `x1`, `y1`, `x2`, `y2`                              |

---

### `Paragraph` object

Groups multiple `Block` objects into one logical field. `text` is the concatenation of all blocks.
Empty for the `default` template.

```json
{
  "tag": "placeIssued",
  "text": "UVD GOR.OZЕРСКА CHELYABINSK REGION",
  "prob": 1.0,
  "loc": {
    "x1": 234,
    "y1": 96,
    "x2": 439,
    "y2": 181
  },
  "blocks": [
    {
      "text": "UVD",
      "tag": "placeIssued",
      "prob": 1.0,
      "loc": {
        "x1": 313,
        "y1": 96,
        "x2": 355,
        "y2": 111
      }
    },
    {
      "text": "GOR.OZЕРSKA",
      "tag": "placeIssued",
      "prob": 1.0,
      "loc": {
        "x1": 327,
        "y1": 131,
        "x2": 422,
        "y2": 147
      }
    },
    {
      "text": "CHELYABINSK",
      "tag": "placeIssued",
      "prob": 1.0,
      "loc": {
        "x1": 234,
        "y1": 164,
        "x2": 384,
        "y2": 181
      }
    },
    {
      "text": "REGION",
      "tag": "placeIssued",
      "prob": 1.0,
      "loc": {
        "x1": 395,
        "y1": 166,
        "x2": 439,
        "y2": 179
      }
    }
  ]
}
```

---

### `Table` object

Present when processing the `default` template (general documents with tables) and `agreement`. `cells` is a 2D array of rows and
columns.

```json
{
  "cells": [
    [
      {
        "tag": "header",
        "text": "Code",
        "prob": 1.0,
        "colspan": 1,
        "rowspan": 1,
        "loc": {
          "x1": 358,
          "y1": 334,
          "x2": 402,
          "y2": 386
        },
        "blocks": [
          {
            "text": "Code",
            "tag": "header",
            "prob": 1.0,
            "loc": {
              "x1": 358,
              "y1": 334,
              "x2": 402,
              "y2": 386
            }
          }
        ]
      }
    ],
    [
      {
        "tag": "data",
        "text": "796",
        "prob": 1.0,
        "colspan": 1,
        "rowspan": 1,
        "loc": {
          "x1": 358,
          "y1": 386,
          "x2": 402,
          "y2": 455
        },
        "blocks": [
          {
            "text": "796",
            "tag": "data",
            "prob": 1.0,
            "loc": {
              "x1": 358,
              "y1": 386,
              "x2": 402,
              "y2": 455
            }
          }
        ]
      }
    ]
  ]
}
```

| Cell field | Type   | Description                              |
|------------|--------|------------------------------------------|
| `tag`      | string | `header` — column header, `data` — value |
| `text`     | string | Cell text                                |
| `prob`     | float  | Confidence (0–1)                         |
| `colspan`  | int    | Column span                              |
| `rowspan`  | int    | Row span                                 |
| `loc`      | object | Cell bounding box                        |
| `blocks`   | array  | Individual blocks inside the cell        |

---

### Passport field tags

| Tag                  | Description                |
|----------------------|----------------------------|
| `lastName`           | Last name                  |
| `firstName`          | First name                 |
| `middleName`         | Middle name / Patronymic   |
| `birthday`           | Date of birth              |
| `birthPlace`         | Place of birth             |
| `gender`             | Gender                     |
| `dateIssued`         | Date of issue              |
| `placeIssued`        | Issued by                  |
| `codeIssued`         | Department code            |
| `ru_passport_number` | Series and passport number |

---

## Code Examples

### Python — sending image as raw binary

```python
import requests

with open("passport.jpg", "rb") as f:
    response = requests.post(
        "http://localhost:8098/processing/passport",
        data=f,
        headers={"Content-Type": "image/jpeg"},
    )

result = response.json()
doc = result["documents"][0]
page = doc["pages"][0]

# Extract all fields by tag from paragraphs
fields = {p["tag"]: p["text"] for p in page["paragraphs"]}
print(fields)
# {'birthPlace': 'CITY.', 'codeIssued': '741-002', 'dateIssued': '16.03.2007', ...}
```

### Python — sending via multipart/form-data

```python
import requests

with open("snils.jpg", "rb") as f:
    response = requests.post(
        "http://localhost:8098/processing/snils",
        files={"file": ("snils.jpg", f, "image/jpeg")},
    )

result = response.json()
page = result["documents"][0]["pages"][0]
fields = {p["tag"]: p["text"] for p in page["paragraphs"]}
print(fields)
```

### Python — iterating over tables (default template)

```python
import requests

with open("balance.jpg", "rb") as f:
    response = requests.post(
        "http://localhost:8098/processing/default",
        data=f,
        headers={"Content-Type": "image/jpeg"},
    )

page = response.json()["documents"][0]["pages"][0]
for table in page["tables"]:
    for row in table["cells"]:
        print([cell["text"] for cell in row])
```

### Python — get all blocks from a page

```python
import requests

with open("document.png", "rb") as f:
    response = requests.post(
        "http://localhost:8098/processing/default",
        data=f,
        headers={"Content-Type": "image/png"},
    )

page = response.json()["documents"][0]["pages"][0]
for block in page["blocks"]:
    print(block["text"], block["tag"], block["prob"], block["loc"])
```

### curl — health check

```bash
curl -X POST http://localhost:8098/health
```

### curl — passport recognition

```bash
curl -X POST http://localhost:8098/processing/passport \
  -H "Content-Type: image/jpeg" \
  --data-binary @passport.jpg
```
