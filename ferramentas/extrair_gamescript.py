"""Extrai o catalogo de falas de ``GameScript/Script.bytes``.

Aceita tanto o bundle UnityFS original quanto o script binario ja extraido.
Os identificadores de cada texto sao offsets da fonte binaria: nao devem mudar
durante a traducao. Este programa somente le os arquivos do jogo.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import struct
from pathlib import Path


LANGUAGES = ("en", "es", "zh", "fr", "de", "it", "nl", "ru")
LANGUAGE_IDS = (10, 34, 40, 14, 15, 21, 9, 30)
HEADER = struct.pack("<II", len(LANGUAGES), LANGUAGE_IDS[0])


def load_script(source: Path) -> bytes:
    """Le bytes crus do TextAsset, sem converter caracteres invalidos."""
    raw = source.read_bytes()
    if not raw.startswith(b"UnityFS"):
        return raw

    import UnityPy  # dependencia local de analise; nao altera o jogo

    environment = UnityPy.load(str(source))
    text_asset = next(
        obj.read()
        for obj in environment.objects
        if obj.type.name == "TextAsset" and obj.read().m_Name == "Script"
    )
    # UnityPy usa surrogateescape para bytes que nao sao UTF-8. A mesma
    # estrategia ao codificar reconstroi exatamente o m_Script serializado.
    return text_asset.m_Script.encode("utf-8", "surrogateescape")


def read_entry(data: bytes, offset: int) -> tuple[int, bytes, int] | None:
    """Le ``[id de idioma][comprimento][bytes UTF-8]``."""
    if offset + 8 > len(data):
        return None
    language_id, length = struct.unpack_from("<II", data, offset)
    end = offset + 8 + length
    if length > 65536 or end > len(data):
        return None
    return language_id, data[offset + 8 : end], end


def decode(raw: bytes) -> str | None:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def valid_english(value: str) -> bool:
    """Aceita texto UTF-8 legível, incluindo reticências e aspas tipográficas."""
    return bool(value) and all(char.isprintable() or char in "\n\t" for char in value)


def extract(data: bytes) -> list[dict[str, str]]:
    """Localiza tabelas de oito idiomas e as converte em linhas de CSV."""
    rows: dict[int, dict[str, str]] = {}
    offset = 0
    while True:
        header = data.find(HEADER, offset)
        if header < 0:
            break
        offset = header + 1

        cursor = header + 4
        values: list[str] = []
        ids: list[int] = []
        for _ in LANGUAGES:
            entry = read_entry(data, cursor)
            if entry is None:
                break
            language_id, raw, cursor = entry
            value = decode(raw)
            if value is None:
                break
            ids.append(language_id)
            values.append(value)

        if len(values) != len(LANGUAGES) or tuple(ids) != LANGUAGE_IDS:
            continue
        if not valid_english(values[0]):
            continue

        english_offset = header + 12
        row = {language: value for language, value in zip(LANGUAGES, values)}
        row.update(
            {
                "id": f"gamescript:{english_offset:08X}",
                "offset": str(english_offset),
                "pt_br": "",
                "status": "pending",
                "notes": "",
            }
        )
        rows[english_offset] = row

    return [rows[key] for key in sorted(rows)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="bundle UnityFS ou Script.bytes")
    parser.add_argument("output", type=Path, help="CSV PT-BR a criar")
    parser.add_argument("--dump-raw", type=Path, help="salva os bytes originais do TextAsset")
    arguments = parser.parse_args()

    data = load_script(arguments.input)
    if arguments.dump_raw:
        arguments.dump_raw.parent.mkdir(parents=True, exist_ok=True)
        arguments.dump_raw.write_bytes(data)

    rows = extract(data)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    fields = ("id", "offset", *LANGUAGES, "pt_br", "status", "notes")
    with arguments.output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"SHA-256 do GameScript: {hashlib.sha256(data).hexdigest()}")
    print(f"{len(rows)} entradas extraidas para {arguments.output}")


if __name__ == "__main__":
    main()
