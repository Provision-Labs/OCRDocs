# Provision.scan — OCR-сервис распознавания документов

C++ реализация сервиса OCR и распознавания документов. Полностью совместима с оригинальной Python/aiohttp версией.

---

## Содержание

- [Установка и запуск](#установка-и-запуск)
    - [Windows](#windows)
    - [Linux](#linux)
    - [Docker](#docker)
- [Эндпоинты API](#эндпоинты-api)
    - [Health](#health)
    - [Перезагрузка моделей](#перезагрузка-моделей)
    - [Распознавание документа (processing)](#распознавание-документа-processing)
    - [Распознавание документа (processing2)](#распознавание-документа-processing2)
- [Шаблоны документов](#шаблоны-документов)
- [Форматы входных данных](#форматы-входных-данных)
- [Формат ответа](#формат-ответа)
- [Примеры кода](#примеры-кода)

---

## Установка и запуск

### Windows

### `Установка`

1. Скачайте [установочный файл](https://provlabs.tech/downloads/provision_ocr_trial_setup.exe)
2. Запустите `provision_ocr_trial.exe`
3. В открывшемся окне выберите язык, путь для установки программы
4. Нажмите `Установить`

### `Запуск`

1. В открывшемся консольном окне дождитесь статуса `Provision Scan: READY`
2. В поле `Listening on` будет указан URL для API
3. Из папки, в которой установлен OCR запустите файл `ProvisionOCR.exe`

### Linux

`В разработке`

### Docker

1. Скачайте docker образ:

```bash
docker pull registry.provlabs.tech/hub/trial/provision_ocr:latest
```

2. Запустите контейнер:

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

> `--gpus all` тег для запуска на GPU. Для запуска на CPU или MacOS нужно исключить данный тег

3. Проверьте, что контейнер запущен:

```bash
docker ps
```

После успешного старта сервис доступен по адресам:

- API:          `http://localhost:8098/`
- Swagger UI:   `http://localhost:8098/docs`
- Health check: `http://localhost:8098/health`

4. Остановка контейнера:

```bash
docker stop provision_ocr
```

---

## Эндпоинты API

### Health

```
POST /health
```

Проверка доступности сервиса (liveness probe).

**Ответы:**

| Код   | Описание                                         |
|-------|--------------------------------------------------|
| `200` | Сервис работает нормально                        |
| `503` | Сервис временно недоступен (middleware отключён) |

**Пример ответа (200):**

```json
{
  "status": "ok"
}
```

---

### Перезагрузка моделей

```
POST /reload_service
```

Выгружает и перезагружает все ONNX-модели при следующем запросе: Mask R-CNN, CRAFT, TextRecognizer, CharRecognizer,
EfficientNet, Edge. Полезно после замены весов на диске без перезапуска сервиса.

**Ответы:**

| Код   | Описание             |
|-------|----------------------|
| `200` | Перезагрузка принята |

**Пример ответа (200):**

```json
{
  "status": "ok"
}
```

---

### Распознавание документа (processing)

```
POST /processing/{template}
```

Основной эндпоинт распознавания. Принимает изображение как в бинарном виде, так и через multipart/form-data.

**Параметры пути:**

| Параметр   | Тип    | Описание                                                         |
|------------|--------|------------------------------------------------------------------|
| `template` | string | Шаблон документа (см. [Шаблоны документов](#шаблоны-документов)) |

**Тело запроса:** изображение в бинарном виде или multipart с полем `body` / `file`.

**Ответы:**

| Код   | Описание                                                                          |
|-------|-----------------------------------------------------------------------------------|
| `200` | Результат распознавания                                                           |
| `400` | Некорректный запрос (отсутствует поле file, неизвестный шаблон, ошибка пайплайна) |
| `415` | Неподдерживаемый формат изображения                                               |

---

### Распознавание документа (processing2)

```
POST /processing2/{template}
```

**Параметры:** аналогично `/processing/{template}`.

---

## Шаблоны документов

| Шаблон      | Описание              |
|-------------|-----------------------|
| `passport`  | Паспорт гражданина РФ |
| `snils`     | СНИЛС                 |
| `agreement` | Договор               |
| `default`   | Универсальный шаблон  |

---

## Форматы входных данных

Сервис принимает изображения в следующих форматах:

| MIME-тип              | Формат                                          |
|-----------------------|-------------------------------------------------|
| `image/jpeg`          | JPEG                                            |
| `image/png`           | PNG                                             |
| `image/bmp`           | BMP                                             |
| `image/tiff`          | TIFF                                            |
| `image/gif`           | GIF  (static)                                   |
| `image/webp`          | WEBP                                            |
| `image/png`           | PDF (сервис сам определит, что пришел документ) |
| `multipart/form-data` | Поле `file` или `body` с изображением           |

---

## Формат ответа

### Структура верхнего уровня

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

| Поле             | Тип   | Описание                        |
|------------------|-------|---------------------------------|
| `width`          | int   | Ширина изображения в пикселях   |
| `height`         | int   | Высота изображения в пикселях   |
| `schema_version` | int   | Версия формата ответа           |
| `pages`          | array | Страницы документа (обычно 1–2) |

---

### Объект `Page`

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

| Поле          | Тип    | Описание                                                                   |
|---------------|--------|----------------------------------------------------------------------------|
| `page_number` | int    | Номер страницы (начиная с 1)                                               |
| `loc`         | object | Bounding box страницы в пикселях                                           |
| `blocks`      | array  | Плоский список всех распознанных блоков на странице                        |
| `paragraphs`  | array  | Сгруппированные блоки; для документов с шаблоном — основной источник полей |
| `tables`      | array  | Распознанные таблицы (пусто для шаблонов паспорт/СНИЛС)                    |
| `figures`     | array  | Обнаруженные фигуры/изображения                                            |

---

### Объект `Block`

Встречается в `page.blocks`, `paragraph.blocks` и `table.cells[r][c].blocks`.

```json
{
  "text": "ИВАНОВ",
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

| Поле   | Тип    | Описание                                                                         |
|--------|--------|----------------------------------------------------------------------------------|
| `text` | string | Распознанный текст блока                                                         |
| `tag`  | string | Семантический тег (например, `lastName`, `dateIssued`, `word`, `header`, `data`) |
| `prob` | float  | Уверенность распознавания (0–1)                                                  |
| `loc`  | object | Bounding box блока: `x1`, `y1`, `x2`, `y2`                                       |

---

### Объект `Paragraph`

Группирует несколько `Block`-ов в одно логическое поле. `text` — конкатенация всех блоков.
Пустое в шаблоне `default`

```json
{
  "tag": "placeIssued",
  "text": "УВД ГОР.ОЗЕРСКА ЧЕЛЯБИНСКОЙ ОБЛ",
  "prob": 1.0,
  "loc": {
    "x1": 234,
    "y1": 96,
    "x2": 439,
    "y2": 181
  },
  "blocks": [
    {
      "text": "УВД",
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
      "text": "ГОР.ОЗЕРСКА",
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
      "text": "ЧЕЛЯБИНСКОЙ",
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
      "text": "ОБЛ",
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

### Объект `Table`

Присутствует при обработке шаблона `default` (общие документы с таблицами). `cells` — двумерный массив строк и столбцов.

```json
{
  "cells": [
    [
      {
        "tag": "header",
        "text": "Код",
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
            "text": "Код",
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

| Поле ячейки | Тип    | Описание                              |
|-------------|--------|---------------------------------------|
| `tag`       | string | `header` — заголовок, `data` — данные |
| `text`      | string | Текст ячейки                          |
| `prob`      | float  | Уверенность (0 — 1)                   |
| `colspan`   | int    | Объединение столбцов                  |
| `rowspan`   | int    | Объединение строк                     |
| `loc`       | object | Bounding box ячейки                   |
| `blocks`    | array  | Отдельные блоки внутри ячейки         |

---

### Теги полей паспорта

| Тег                  | Описание               |
|----------------------|------------------------|
| `lastName`           | Фамилия                |
| `firstName`          | Имя                    |
| `middleName`         | Отчество               |
| `birthday`           | Дата рождения          |
| `birthPlace`         | Место рождения         |
| `gender`             | Пол                    |
| `dateIssued`         | Дата выдачи            |
| `placeIssued`        | Кем выдан              |
| `codeIssued`         | Код подразделения      |
| `ru_passport_number` | Серия и номер паспорта |

---

## Примеры кода

### Python — передача изображения в бинарном виде

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

# Извлечь все поля по тегу из параграфов
fields = {p["tag"]: p["text"] for p in page["paragraphs"]}
print(fields)
# {'birthPlace': 'ГОР.', 'codeIssued': '741-002', 'dateIssued': '16.03.2007', ...}
```

### Python — передача через multipart/form-data

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

### Python — обход таблиц (шаблон default)

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

### Python — получить все блоки со страницы

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

### curl — проверка доступности

```bash
curl -X POST http://localhost:8098/health
```

### curl — распознавание паспорта

```bash
curl -X POST http://localhost:8098/processing/passport \
  -H "Content-Type: image/jpeg" \
  --data-binary @passport.jpg
```
