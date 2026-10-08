#!/usr/bin/env python3
"""Inventário somente-leitura de um projeto para a fase de contexto da skill `audit`.

Uso: python inventario.py <diretorio-alvo>

Não modifica nenhum arquivo. Lista manifestos, linguagens (arquivos/LOC), maiores arquivos
e rotas HTTP detectadas por regex simples (FastAPI/Flask/Express).
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

IGNORAR = {".git", "node_modules", "dist", "build", "__pycache__", ".pytest_cache",
           ".venv", "venv", ".mypy_cache", "coverage"}
EXT_LING = {".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript/JSX", ".ts": "TypeScript",
            ".tsx": "TypeScript/TSX", ".css": "CSS", ".html": "HTML", ".sql": "SQL",
            ".yml": "YAML", ".yaml": "YAML", ".json": "JSON", ".toml": "TOML", ".md": "Markdown"}
MANIFESTOS = {"requirements.txt", "requirements-dev.txt", "pyproject.toml", "package.json",
              "package-lock.json", "Dockerfile", "compose.yaml", "docker-compose.yml",
              "vite.config.js", "playwright.config.js", "pytest.ini", "setup.cfg"}
ROTA = re.compile(r"@(?:app|router|\w+)\.(get|post|put|patch|delete)\(\s*[\"']([^\"']+)")
ROTA_JS = re.compile(r"\b(?:app|router)\.(get|post|put|patch|delete)\(\s*[\"'`]([^\"'`]+)")


def arquivos(raiz: Path):
    for p in raiz.rglob("*"):
        if p.is_file() and not any(parte in IGNORAR for parte in p.relative_to(raiz).parts):
            yield p


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    raiz = Path(sys.argv[1]).resolve()
    if not raiz.is_dir():
        print(f"Diretório inválido: {raiz}")
        return 2

    por_ling: Counter[str] = Counter()
    loc_ling: Counter[str] = Counter()
    tamanhos: list[tuple[int, str]] = []
    manifestos: list[str] = []
    rotas: list[str] = []

    for p in arquivos(raiz):
        rel = p.relative_to(raiz).as_posix()
        if p.name in MANIFESTOS:
            manifestos.append(rel)
        ling = EXT_LING.get(p.suffix.lower())
        if not ling:
            continue
        try:
            texto = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        linhas = texto.count("\n") + 1
        por_ling[ling] += 1
        loc_ling[ling] += linhas
        tamanhos.append((linhas, rel))
        padrao = ROTA if p.suffix == ".py" else ROTA_JS if p.suffix in {".js", ".ts"} else None
        if padrao:
            for n, linha in enumerate(texto.splitlines(), 1):
                m = padrao.search(linha)
                if m:
                    rotas.append(f"{m.group(1).upper():6} {m.group(2):40} {rel}:{n}")

    print(f"# Inventário: {raiz}\n")
    print("## Manifestos")
    for m in sorted(manifestos):
        print(f"- {m}")
    print("\n## Linguagens (arquivos / linhas)")
    for ling, qtd in por_ling.most_common():
        print(f"- {ling}: {qtd} / {loc_ling[ling]}")
    print("\n## Maiores arquivos")
    for linhas, rel in sorted(tamanhos, reverse=True)[:10]:
        print(f"- {rel}: {linhas} linhas")
    print("\n## Rotas HTTP detectadas")
    for r in rotas or ["(nenhuma)"]:
        print(f"- {r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
