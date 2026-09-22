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
    - [License Status](#license-status)
    - [License Activation](#license-activation)
    - [Document Recognition (processing)](#document-recognition-processing)
    - [Document Recognition (processing2)](#document-recognition-processing2)
- [Document Templates](#document-templates)
- [Input Formats](#input-formats)
- [Query Parameters](#query-parameters)
- [PDF Processing](#pdf-processing)
- [Response Format](#response-format)
- [Code Examples](#code-examples)

---

## Installation and Launch

### Windows

### `Installation`

1. Download the [installer](https://provlabs.tech/downloads/provision_ocr_setup.exe)
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
docker pull registry.provlabs.tech/hub/provision_ocr:latest
```

2. Run the container:

**CMD / bash:**

```bash
docker run -d --name provision_ocr --gpus all -p 8098:8098 --restart always registry.provlabs.tech/hub/provision_ocr:latest
```

**PowerShell:**

```powershell
docker run -d `
  --name provision_ocr `
  --gpus all `
  -p 8098:8098 `
  --restart always `
  registry.provlabs.tech/hub/provision_ocr:latest
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

Service availability check (liveness probe). Returns `503` when the service middleware is disabled.

**Responses:**

| Code  | Description                                      |
|-------|--------------------------------------------------|
| `200` | Service is running normally                      |
| `503` | Service temporarily unavailable (middleware off) |

**Example response (200):**

```json
{
  "status": "ok",
  "version": "0.9.3"
}
```

`version` is the product version of the running build (from the `VERSION` file at compile time), independent of the
version of this API contract. It reads `"unknown"` only if the build was made without the version define.

---

### Reload Models

```
POST /reload_service
```

Re-reads `provision_ocr.ini` (the `[weights]` per-model path overrides and the `text_*_img_w` input widths) and the
per-template JSON configs, then drops all loaded **TorchScript** sessions: Mask R-CNN, CRAFT, TextRecognizer,
CharRecognizer, EfficientNet, Edge. Sessions are lazily re-instantiated on the next request, so the weights can be
swapped on disk without restarting the process.

The ini file is parsed and validated as a whole **before** anything is applied — if a value fails to parse, the request
answers `400` naming the offending key and the running configuration is left untouched.

The reload waits for in-flight inference jobs to drain, so the response can take a few seconds. Only one reload runs at
a time; a second call while one is in progress receives `409`.

This endpoint is restricted by the admin allowlist (`reload_allow`) — callers whose IP is not on the list receive `403`.

**Responses:**

| Code  | Description                                                                                  |
|-------|----------------------------------------------------------------------------------------------|
| `200` | Reload done — sessions dropped, models are re-created on the next request                    |
| `400` | `provision_ocr.ini` failed validation — `message` names the key, the value and the file:line |
| `403` | Caller IP is not in the `reload_allow` list                                                  |
| `409` | A reload is already in progress — retry after it finishes                                    |
| `500` | Reload failed after validation (weights directory unreadable, sessions could not be dropped) |

**Example response (200):**

```json
{
  "status": "ok",
  "config_reloaded": true
}
```

`config_reloaded` is `false` when the process was started without a config directory (tests / embedders).

---

### License Status

```
GET /license/status
```

Read-only snapshot of the local license subsystem. This endpoint is excluded from the license gate, so dashboards can
poll it even on a broken or expired license. It does **not** include machine-identifying or signing-key material.
Specific deny reasons (fingerprint mismatch, request-limit reached, tampered counter, etc.) surface in the per-request
`403` body of the recognition endpoints, not here.

**Responses:**

| Code  | Description              |
|-------|--------------------------|
| `200` | Current license snapshot |

**Example response (200):**

```json
{
  "mode": "online",
  "status": "valid",
  "used": 1204,
  "limit": 50000,
  "windowResetsAt": "2026-10-15T00:00:00Z",
  "expiresAt": "2027-09-01T00:00:00Z",
  "product": "OCR",
  "tariff": "BUSINESS"
}
```

| Field            | Type    | Description                                                                                                     |
|------------------|---------|-----------------------------------------------------------------------------------------------------------------|
| `mode`           | string  | `trial`, `online`, `offline`, `none` (uninitialised / unknown / token-stub)                                     |
| `status`         | string  | `valid`, `expired`, `none` (other deny reasons collapse to `none` and surface only in per-request `403` bodies) |
| `used`           | integer | Requests served against the active counter in the current 30-day window                                         |
| `limit`          | integer | Request limit for the 30-day window. `-1` = no quota, `0` = no license at all, positive = per-window budget     |
| `windowResetsAt` | string  | RFC 3339 UTC instant the 30-day counter resets. Empty when `limit` is `0` or `-1`                               |
| `expiresAt`      | string  | RFC 3339 UTC instant the license itself expires. Empty when there's no `.lic` loaded                            |
| `product`        | string  | Product line the `.lic` is bound to (e.g. `OCR`). Empty when no `.lic`                                          |
| `tariff`         | string  | Plan tier from the `.lic` (e.g. `BUSINESS`). Empty when no `.lic`                                               |

---

### License Activation

```
POST /license/activate
```

Submits an activation code to the License Server, persists the returned signed `.lic` file and re-initialises the
license subsystem — no restart needed. Idempotent for the same machine + code: the server returns the cached `.lic`
without consuming a new slot.

This endpoint is excluded from the license gate, so a locked (unlicensed / expired) server can still be activated. It is
restricted by the admin allowlist (`reload_allow`) — callers not on the list receive `403`. The License Server
round-trip may take up to 15 seconds, and only one activation runs at a time — a second call while one is in progress
receives `409`.

**Request body:**

```json
{
  "activationCode": "XXXX-XXXX-XXXX-XXXX"
}
```

**Responses:**

| Code  | Description                                                                                                        |
|-------|--------------------------------------------------------------------------------------------------------------------|
| `200` | Activated — license snapshot with `activated: true`                                                                |
| `400` | `activationCode` field missing or empty                                                                            |
| `403` | Caller IP is not in the `reload_allow` list                                                                        |
| `409` | Another activation is already in progress on this server — retry after it finishes                                 |
| `501` | License subsystem disabled at compile time (`PROVISION_NO_LICENSE` build)                                          |
| `502` | Activation failed — wrong / revoked code, no free slot, or License Server unreachable; `detail` carries the reason |

**Example response (200):**

```json
{
  "mode": "online",
  "status": "valid",
  "used": 0,
  "limit": 50000,
  "windowResetsAt": "2026-10-22T00:00:00Z",
  "expiresAt": "2027-09-01T00:00:00Z",
  "product": "OCR",
  "tariff": "BUSINESS",
  "activated": true,
  "detail": "activated in online mode"
}
```

---

### Document Recognition (processing)

```
POST /processing/{template}
```

Main recognition endpoint. Accepts a raw image body, a PDF, or a multipart upload (`file` or `body` field).

**Path parameters:**

| Parameter  | Type   | Description                                                       |
|------------|--------|-------------------------------------------------------------------|
| `template` | string | Document template (see [Document Templates](#document-templates)) |

**Query parameters:** see [Query Parameters](#query-parameters).

**Request body:** image or PDF as raw binary, or multipart with field `body` / `file`.

**Responses:**

| Code  | Description                                                                                                           |
|-------|-----------------------------------------------------------------------------------------------------------------------|
| `200` | Recognition result                                                                                                    |
| `400` | Bad request: missing file field, unknown template, invalid `language`/`pagesFrom`/`pagesTo`, unreadable/encrypted PDF |
| `415` | Image payload could not be decoded                                                                                    |
| `500` | Internal error while processing (model not loaded, CUDA error, template config that does not parse)                   |
| `503` | GPU inference queue is saturated — retry per `Retry-After` header                                                     |

---

### Document Recognition (processing2)

```
POST /processing2/{template}
```

Alias of `/processing/{template}` — same handler, same accepted media types, same query parameters and response codes.
Kept for backwards compatibility with legacy clients that used the `/processing2` path.

---

## Document Templates

| Template     | Description                  | Data               | Supported formats  |
|--------------|------------------------------|--------------------|--------------------|
| `passport`   | Russian Federation passport  | paragraphs         | image, scanned-pdf |
| `snils`      | SNILS (pension certificate)  | paragraphs         | image, scanned-pdf |
| `agreement`  | Contract / Agreement         | paragraphs, tables | image, scanned-pdf |
| `regulation` | Regulation / internal policy | blocks, tables     | image, scanned-pdf |
| `default`    | Universal template           | blocks, tables     | image, pdf (all)   |

---

## Input Formats

The service accepts images and documents in the following formats:

| MIME type             | Format                                             |
|-----------------------|----------------------------------------------------|
| `image/jpeg`          | JPEG                                               |
| `image/png`           | PNG                                                |
| `image/bmp`           | BMP                                                |
| `image/tiff`          | TIFF                                               |
| `image/gif`           | GIF (static)                                       |
| `image/webp`          | WEBP                                               |
| `application/pdf`     | PDF (multi-page, split and processed page-by-page) |
| `multipart/form-data` | Field `file` or `body` containing the image/PDF    |

---

## Query Parameters

Both `/processing/{template}` and `/processing2/{template}` accept the same query parameters:

| Parameter   | Type            | Default     | Description                                                                                                                                                                                                                                                          |
|-------------|-----------------|-------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `language`  | array of string | `[rus,eng]` | Recognizer selection, comma-separated (the parameter may also repeat). See table below. Unknown values → `400`.                                                                                                                                                      |
| `pagesFrom` | integer         | `0`         | **PDF only.** First page to process, 0-based, inclusive. Ignored for images.                                                                                                                                                                                         |
| `pagesTo`   | integer         | last page   | **PDF only.** End of the page range, **exclusive** (`pagesFrom=0&pagesTo=3` = first three pages). Must be `>= pagesFrom`, otherwise `400`. A range outside the document is not an error — the response is `200` with an empty `pages` array and the real `maxPages`. |

**`language` values:**

| Value                    | Behavior                                                                                                                                                                                                                      |
|--------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| *(omitted)* or `rus,eng` | Printed text, every character of both scripts (Cyrillic and Latin) via the automatic script router, no filter.                                                                                                                |
| `rus`                    | Everything read with the Russian recognizer.                                                                                                                                                                                  |
| `eng`                    | Everything read with the Latin recognizer; output limited to digits, punctuation, symbols and ASCII letters. A letter outside that set is not transliterated but replaced by the most probable allowed one (`café` → `cafe`). |
| `literal_rus`            | **Handwritten** Russian (mask-based word detection + handwriting CRNN; table extraction disabled). Any combination that includes `literal_rus` also runs the handwritten-Russian path.                                        |

---

## PDF Processing

PDF inputs are split into pages and processed page-by-page; the multi-page result is merged into a single `pages` array
on the `Document` object, in the same way as for a multi-page image.

The optional `pagesFrom` / `pagesTo` query parameters limit processing to a page window. When a PDF is submitted, the
response's `Document` object carries three extra fields (absent for image inputs):

| Field       | Description                                                                                                                     |
|-------------|---------------------------------------------------------------------------------------------------------------------------------|
| `pagesFrom` | Requested start of the range (0-based, inclusive), echoed from the query param; `0` when the param was absent.                  |
| `pagesTo`   | Requested end of the range (exclusive), echoed from the query param; the document's total page count when the param was absent. |
| `maxPages`  | The document's real total page count, regardless of the requested range — lets clients paginate without a probe request.        |

`page_number` values inside `pages` are always the **original** document positions (1-based), not renumbered relative to
the requested window.

If every page in the requested range fails to process, the endpoint returns `500` with a message prefixed `page N:`. If
only some pages fail, the response is still `200`, the failed pages are simply absent from `pages` (detectable as gaps
in `page_number` against `pagesFrom`/`pagesTo`), and one error line per failed page is written to the server log.

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

| Field            | Type   | Description                                                                             |
|------------------|--------|-----------------------------------------------------------------------------------------|
| `width`          | int    | Width of the original input in pixels (or PDF points)                                   |
| `height`         | int    | Height of the original input in pixels (or PDF points)                                  |
| `schema_version` | number | Response format version                                                                 |
| `pages`          | array  | Document pages (usually 1–2 for images; up to the PDF's page count)                     |
| `pagesFrom`      | int    | **PDF only.** Requested start of the page range (see [PDF Processing](#pdf-processing)) |
| `pagesTo`        | int    | **PDF only.** Requested end of the page range                                           |
| `maxPages`       | int    | **PDF only.** Document's real total page count                                          |

---

### `Page` object

```json
{
  "page_number": 1,
  "rotation": 0,
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

| Field         | Type   | Description                                                                                                                                                                                                                                                                                                                                                                                                                                     |
|---------------|--------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `page_number` | int    | Page number (starting from 1, original document position)                                                                                                                                                                                                                                                                                                                                                                                       |
| `rotation`    | number | Clockwise angle, in degrees, the page as delivered must be turned so its text reads upright. `0` = already upright, `90`/`180`/`-90` = quarter turns. On OCR'd pages this also includes the residual skew correction (e.g. `-7.43`) when `page_deskew` is enabled. Absent when the orientation net is disabled, its weights are missing, the template opts out, or the net wasn't confident enough to act — absence is **not** the same as `0`. |
| `loc`         | object | Page bounding box in pixels                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `blocks`      | array  | Flat list of all recognized blocks on the page                                                                                                                                                                                                                                                                                                                                                                                                  |
| `paragraphs`  | array  | Grouped blocks; present only for `passport`/`snils` templates                                                                                                                                                                                                                                                                                                                                                                                   |
| `tables`      | array  | Recognized tables (empty for `passport`/`snils` templates)                                                                                                                                                                                                                                                                                                                                                                                      |
| `figures`     | array  | Reserved for future use; currently always `[]`                                                                                                                                                                                                                                                                                                                                                                                                  |

---

### `Block` object

Found in `page.blocks`, `paragraph.blocks`, and `table.cells[r][c].blocks`.

```json
{
  "text": "IVANOV",
  "tag": "lastName",
  "prob": 1.0,
  "det_prob": 1.0,
  "loc": {
    "x1": 328,
    "y1": 515,
    "x2": 422,
    "y2": 528
  }
}
```

| Field      | Type   | Description                                                                                                                                                                                                                                        |
|------------|--------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `text`     | string | Recognized text of the block                                                                                                                                                                                                                       |
| `tag`      | string | Semantic tag (e.g., `lastName`, `dateIssued`, `word`, `header`, `data`)                                                                                                                                                                            |
| `prob`     | float  | Recognition confidence: per-character-normalized CTC forward probability of `text` given the crop (0–1)                                                                                                                                            |
| `det_prob` | float  | Detection confidence of the box itself. Orthogonal to `prob`: a high `prob` with a low `det_prob` means a confidently recognized but dubious region. Omitted when the box did not come from the CRAFT detector (mask-derived fields, handwriting). |
| `loc`      | object | Block bounding box: `x1`, `y1`, `x2`, `y2`                                                                                                                                                                                                         |

---

### `Paragraph` object

Groups multiple `Block` objects into one logical field. `text` is the concatenation of all blocks. Emitted only for the
`passport` and `snils` templates — `default`, `agreement`, and `regulation` omit this key.

```json
{
  "tag": "placeIssued",
  "text": "UVD GOR.OZЕРSKA CHELYABINSK REGION",
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
      "det_prob": 1.0,
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
      "det_prob": 1.0,
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
      "det_prob": 1.0,
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
      "det_prob": 1.0,
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

Present when processing the `default`, `agreement`, and `regulation` templates. `cells` is a row-major 2D array: the
outer array is rows, the inner array is the cells of that row.

```json
{
  "table_number": 1,
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
            "det_prob": 1.0,
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
        "det_prob": 1.0,
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
            "det_prob": 1.0,
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

`table_number` (1-based) identifies the table on the page.

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

### Python — recognizing a PDF page range with handwritten Russian

```python
import requests

with open("form.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8098/processing/default",
        params={"language": "literal_rus", "pagesFrom": 0, "pagesTo": 3},
        data=f,
        headers={"Content-Type": "application/pdf"},
    )

doc = response.json()["documents"][0]
print(doc["pagesFrom"], doc["pagesTo"], doc["maxPages"])
```

### Python — checking license status

```python
import requests

response = requests.get("http://localhost:8098/license/status")
print(response.json())
```

### Python — activating a license

```python
import requests

response = requests.post(
    "http://localhost:8098/license/activate",
    json={"activationCode": "XXXX-XXXX-XXXX-XXXX"},
)
print(response.json())
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

### curl — reload models and configs

```bash
curl -X POST http://localhost:8098/reload_service
```