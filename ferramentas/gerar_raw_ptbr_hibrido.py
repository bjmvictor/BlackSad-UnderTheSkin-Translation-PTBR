"""Gera Raw PT-BR híbrido: English normal e empréstimo pontual do slot Español."""
from __future__ import annotations

import argparse
import csv
import struct
from collections import Counter, defaultdict
from pathlib import Path

from gerar_raw_uabea_ptbr import get_script
from gerar_raw_ptbr_slot_fixo import HEADER, LANGUAGE_IDS, LANGUAGES, _entry


def tables(data: bytes | bytearray):
    """Lê as tabelas de oito idiomas, inclusive quando o English não é ASCII."""
    at = 0
    while True:
        header = data.find(HEADER, at)
        if header < 0:
            return
        at = header + 1
        cursor = header + 4
        entries = []
        for expected_id in LANGUAGE_IDS:
            entry = _entry(data, cursor)
            if entry is None or entry[0] != expected_id:
                break
            language_id, text_start, text_end = entry
            entries.append((cursor, language_id, text_start, text_end))
            cursor = text_end
        if len(entries) != len(LANGUAGE_IDS):
            continue
        try:
            source = bytes(data[entries[0][2] : entries[0][3]]).decode("utf-8")
        except UnicodeDecodeError:
            source = ""
        yield source, entries


def raw_script(blob: bytes) -> tuple[int, int, bytes]:
    name_length = struct.unpack_from("<I", blob, 0)[0]
    start = 4 + name_length
    start += (4 - start % 4) % 4
    length = struct.unpack_from("<I", blob, start)[0]
    script = blob[start + 4 : start + 4 + length]
    if len(script) != length:
        raise ValueError("TextAsset .dat inválido")
    return start, length, script


def mapping(catalog: Path) -> dict[str, str]:
    grouped: defaultdict[str, set[str]] = defaultdict(set)
    with catalog.open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            if row.get("pt_br"):
                grouped[row["en"]].add(row["pt_br"])
    return {source: next(iter(values)) for source, values in grouped.items() if len(values) == 1}


def fit(text: str, size: int) -> tuple[bytes, bool]:
    encoded = text.encode("utf-8")
    if len(encoded) <= size:
        return encoded + b" " * (size - len(encoded)), True
    clipped = encoded[:size]
    while clipped:
        try:
            clipped.decode("utf-8")
            break
        except UnicodeDecodeError:
            clipped = clipped[:-1]
    return clipped + b" " * (size - len(clipped)), False


def write_exact(data: bytearray, entry: tuple[int, int, int, int], text: str) -> bool:
    """Grava um texto completo no campo; nunca deixa uma tradução truncada."""
    encoded = text.encode("utf-8")
    capacity = entry[3] - entry[2]
    if len(encoded) > capacity:
        return False
    data[entry[2] : entry[3]] = encoded + b" " * (capacity - len(encoded))
    return True


def write_fallback(data: bytearray, entry: tuple[int, int, int, int], source: str) -> None:
    """Mantém o English original quando nenhum slot consegue conter o PT-BR."""
    encoded, _ = fit(source, entry[3] - entry[2])
    data[entry[2] : entry[3]] = encoded


def generate(
    raw: Path,
    catalog: Path,
    arab_bundle: Path,
    target: Path,
    source_filter: set[str] | None = None,
    override: str | None = None,
) -> None:
    blob = raw.read_bytes()
    start, old_length, original = raw_script(blob)
    base = bytearray(get_script(arab_bundle))
    original_tables = list(tables(original))
    base_tables = list(tables(base))
    if len(original_tables) != len(base_tables):
        raise ValueError("Estruturas original e referência não coincidem")

    translations = mapping(catalog)
    source_filter = source_filter or set()
    if bool(source_filter) != bool(override):
        raise ValueError("Use --only-source e --text juntos, ou nenhum dos dois.")

    fixed = fallback = swapped = 0
    donors_used: Counter[str] = Counter()
    for (source, _), (_, base_entries) in zip(original_tables, base_tables):
        english = base_entries[0]
        value = override if source in source_filter else translations.get(source, source)

        if write_exact(base, english, value):
            fixed += value != source
            continue

        if value != source:
            # Escolhe o maior campo já existente desta tabela. Cada troca é
            # local: English passa a ter o ID do doador e o doador recebe ID 10.
            # Assim, nenhum tamanho de string, offset ou tamanho do script muda.
            donors = sorted(
                enumerate(base_entries[1:], start=1),
                key=lambda item: item[1][3] - item[1][2],
                reverse=True,
            )
            for donor_index, donor in donors:
                if not write_exact(base, donor, value):
                    continue
                write_fallback(base, english, source)
                struct.pack_into("<I", base, english[0], donor[1])
                struct.pack_into("<I", base, donor[0], english[1])
                donors_used[LANGUAGES[donor_index]] += 1
                swapped += 1
                break
            else:
                write_fallback(base, english, source)
                fallback += 1
            continue

        write_fallback(base, english, source)
        fallback += value != source

    padding = b"\0" * ((4 - len(base) % 4) % 4)
    target.write_bytes(blob[:start] + struct.pack("<I", len(base)) + base + padding + blob[start + 4 + old_length :])
    donor_summary = ", ".join(f"{LANGUAGES[key] if isinstance(key, int) else key}:{count}" for key, count in donors_used.items()) or "nenhum"
    print(f"Hibrido gerado: {target}; PT-BR no English em {fixed}; PT-BR emprestado em {swapped} ({donor_summary}); ingles preservado por limite em {fallback}; bytes {target.stat().st_size}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gera Raw híbrido seguro para aplicação via UABEA.")
    parser.add_argument("raw", type=Path)
    parser.add_argument("catalog", type=Path)
    parser.add_argument("arab_bundle", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("--only-source", action="append", help="Sobrescreve pontualmente um texto para teste.")
    parser.add_argument("--text", help="Texto usado junto de --only-source.")
    args = parser.parse_args()
    generate(args.raw, args.catalog, args.arab_bundle, args.target, set(args.only_source or ()), args.text)
