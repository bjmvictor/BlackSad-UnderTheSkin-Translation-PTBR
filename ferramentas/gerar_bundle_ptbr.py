"""Gera uma copia PT-BR do bundle GameScript a partir do catalogo CSV.

Por seguranca, este programa nunca escreve na instalacao da Steam. Ele troca a
coluna inglesa (id 10) pelo texto ``pt_br`` e preserva os outros sete idiomas e
todos os comandos internos. Por padrao exige a traducao completa; ``--allow-
partial`` existe somente para testes locais de interface.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import struct
from collections import defaultdict
from pathlib import Path

import UnityPy


LANGUAGE_IDS = (10, 34, 40, 14, 15, 21, 9, 30)
HEADER = struct.pack("<II", 8, 10)


def raw_script_from_environment(environment: UnityPy.Environment) -> tuple[object, bytes]:
    asset = next(
        obj.read()
        for obj in environment.objects
        if obj.type.name == "TextAsset" and obj.read().m_Name == "Script"
    )
    return asset, asset.m_Script.encode("utf-8", "surrogateescape")


def read_entry(data: bytes, position: int) -> tuple[int, bytes, int] | None:
    if position + 8 > len(data):
        return None
    language_id, length = struct.unpack_from("<II", data, position)
    end = position + 8 + length
    if length > 65536 or end > len(data):
        return None
    return language_id, data[position + 8 : end], end


def records(data: bytes):
    """Retorna (offset, texto ingles, inicio_tamanho, fim_texto) validos."""
    search_at = 0
    while True:
        header = data.find(HEADER, search_at)
        if header < 0:
            return
        search_at = header + 1
        position = header + 4
        entries = []
        for _ in LANGUAGE_IDS:
            entry = read_entry(data, position)
            if entry is None:
                break
            entries.append((position, *entry))
            position = entry[2]
        if len(entries) != 8 or tuple(item[1] for item in entries) != LANGUAGE_IDS:
            continue
        try:
            english = entries[0][2].decode("utf-8")
        except UnicodeDecodeError:
            continue
        if not english.isascii() or not english or any(ord(char) < 32 or ord(char) > 126 for char in english):
            continue
        # entries[0] = (inicio do id, id, bytes, fim); o tamanho fica 4 bytes
        # antes do texto e deve ser ajustado junto da traducao.
        yield header + 12, english, entries[0][0] + 4, entries[0][3]


def translations(catalog: Path, statuses: set[str] | None = None, safe_only: bool = False, resolve_conflicts: bool = False) -> dict[str, str]:
    values: dict[str, list[str]] = defaultdict(list)
    with catalog.open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            if statuses and row.get("status") not in statuses:
                continue
            source = row["en"]
            # Marcadores entre colchetes e chaves curtas podem ser interpretados
            # pelo roteiro/UI. A previa segura nao os altera.
            if safe_only and (source.startswith("[") or source in {"Back", "Not yet"}):
                continue
            translated = row.get("pt_br", "").strip()
            if translated:
                values[source].append(translated)
    unique = {source: set(translated) for source, translated in values.items()}
    conflicts = {source: translated for source, translated in unique.items() if len(translated) > 1}
    if conflicts:
        if not resolve_conflicts:
            sample = next(iter(conflicts.items()))
            raise SystemExit(f"ERRO: ha traducoes conflitantes para {sample[0]!r}: {sorted(sample[1])}")
        print(f"AVISO: {len(conflicts)} textos com variantes PT-BR; o preview usará a variante mais recorrente.")
    return {source: max(set(translated), key=lambda text: (translated.count(text), text)) for source, translated in values.items()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="bundle 2172dc1d... original")
    parser.add_argument("catalog", type=Path, help="texto/catalogo/pt-BR.csv")
    parser.add_argument("target", type=Path, help="destino dentro da pasta do mod")
    parser.add_argument("--allow-partial", action="store_true", help="gera preview mantendo ingles onde faltar PT-BR")
    parser.add_argument("--statuses", help="aplica apenas estes status, separados por virgula")
    parser.add_argument("--safe-only", action="store_true", help="nao altera marcadores ou chaves de UI conhecidas")
    parser.add_argument("--resolve-conflicts", action="store_true", help="para preview, usa a variante PT-BR mais recorrente sem alterar o CSV")
    args = parser.parse_args()

    environment = UnityPy.load(str(args.source))
    asset, original = raw_script_from_environment(environment)
    source_records = list(records(original))
    if not source_records:
        raise SystemExit("ERRO: nao encontrei tabelas localizadas validas no bundle")

    statuses = set(args.statuses.split(",")) if args.statuses else None
    mapping = translations(args.catalog, statuses, args.safe_only, args.resolve_conflicts)
    all_sources = {english for _, english, _, _ in source_records}
    missing = sorted(all_sources - mapping.keys())
    if missing and not args.allow_partial:
        raise SystemExit(
            f"ERRO: faltam {len(missing)} textos distintos. Use --allow-partial apenas para preview local."
        )

    rebuilt = bytearray()
    cursor = 0
    changed = 0
    for _, english, length_position, text_end in source_records:
        translation = mapping.get(english, english)
        encoded = translation.encode("utf-8")
        rebuilt.extend(original[cursor:length_position])
        rebuilt.extend(struct.pack("<I", len(encoded)))
        rebuilt.extend(encoded)
        cursor = text_end
        changed += translation != english
    rebuilt.extend(original[cursor:])

    asset.m_Script = bytes(rebuilt).decode("utf-8", "surrogateescape")
    asset.save()
    bundle = next(iter(environment.files.values()))
    args.target.parent.mkdir(parents=True, exist_ok=True)
    args.target.write_bytes(bundle.save(packer="original"))

    check = UnityPy.load(str(args.target))
    _, written = raw_script_from_environment(check)
    if bytes(rebuilt) != written:
        raise SystemExit("ERRO: o bundle gravado nao reproduz o GameScript remontado")
    print(f"Bundle criado: {args.target}")
    print(f"Textos PT-BR aplicados: {changed} ocorrencias; faltam {len(missing)} textos distintos")
    print(f"SHA-256 do GameScript novo: {hashlib.sha256(written).hexdigest()}")


if __name__ == "__main__":
    main()
