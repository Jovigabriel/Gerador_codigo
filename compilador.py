"""
compilador.py — Orquestrador do compilador Cool → Bril
=======================================================
Fluxo:
    Código-fonte (.cl)
        ↓  lexico.py + parser.py + semantico.py
    AST validada
        ↓  gerador.py
    Código Bril (.bril)
        ↓  bril2json   (instalado via uv)
    JSON
        ↓  brili       (instalado via deno)
    Resultado

Instalação das ferramentas Bril (uma vez só):
    1. Instalar Deno:   https://deno.com
    2. Instalar uv:     https://docs.astral.sh/uv/getting-started/installation/
    3. Instalar brili:
           deno install -g brili.ts
       (dentro da pasta bril/ clonada do GitHub)
    4. Instalar bril2json:
           cd bril/bril-txt
           uv tool install .

Uso:
    python compilador.py arquivo.cl           # gera e executa
    python compilador.py arquivo.cl -o s.bril # salva o .bril sem executar
    python compilador.py arquivo.cl --no-run  # gera mas não executa
"""

import sys
import os
import subprocess
import tempfile
from shutil import which

from lexico import lexer
from parser import parser
from semantico import AnalisadorSemantico
from gerador import GeradorBril


def compilar(codigo_fonte: str, arquivo_saida: str = None, executar: bool = True):

    # ── Fase 1: Léxico + Sintático ────────────────────────────────────────────
    print("[1/3] Análise léxica e sintática...", file=sys.stderr)
    arvore = parser.parse(codigo_fonte, lexer=lexer.clone())
    if arvore is None:
        print("[ERRO] O parser não produziu uma árvore válida.", file=sys.stderr)
        sys.exit(1)

    # ── Fase 2: Semântico ─────────────────────────────────────────────────────
    print("[2/3] Análise semântica...", file=sys.stderr)
    AnalisadorSemantico(arvore).analisar()
    print("[SUCESSO] Sem erros semânticos.\n", file=sys.stderr)

    # ── Fase 3: Geração de código Bril ───────────────────────────────────────
    print("[3/3] Gerando código Bril...", file=sys.stderr)
    gerador = GeradorBril(arvore)
    gerador.gerar()
    codigo_bril = "\n".join(gerador.codigo)
    print(codigo_bril)

    # ── Salvar em arquivo ─────────────────────────────────────────────────────
    if arquivo_saida:
        with open(arquivo_saida, "w", encoding="utf-8") as f:
            f.write(codigo_bril)
        print(f"\n[OK] Código Bril salvo em: {arquivo_saida}", file=sys.stderr)
        bril_path = arquivo_saida
        deletar_temp = False
    else:
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".bril",
                                          delete=False, encoding="utf-8")
        tmp.write(codigo_bril)
        tmp.close()
        bril_path = tmp.name
        deletar_temp = True

    # ── Fase 4: Execução com brili ────────────────────────────────────────────
    if executar:
        _executar_bril(bril_path)

    if deletar_temp:
        os.unlink(bril_path)


def _executar_bril(bril_path: str):
    """
    Pipeline: bril2json < arquivo.bril | brili
    - bril2json: instalado via  uv tool install .  (pasta bril/bril-txt)
    - brili:     instalado via  deno install -g brili.ts
    """
    print("\n[Executando com brili]", file=sys.stderr)

    bril2json_cmd = which("bril2json")
    brili_cmd     = which("brili")

    if not bril2json_cmd:
        print("[AVISO] 'bril2json' não encontrado no PATH.", file=sys.stderr)
        print("  Instale com:", file=sys.stderr)
        print("    cd bril/bril-txt && uv tool install .", file=sys.stderr)
        return

    if not brili_cmd:
        print("[AVISO] 'brili' não encontrado no PATH.", file=sys.stderr)
        print("  Instale com:", file=sys.stderr)
        print("    deno install -g brili.ts   (dentro da pasta bril/)", file=sys.stderr)
        print("  Depois adicione $HOME/.deno/bin ao seu PATH.", file=sys.stderr)
        return

    try:
        with open(bril_path, "r", encoding="utf-8") as f:
            bril_texto = f.read()

        # Passo 1: bril2json
        p1 = subprocess.run(
            [bril2json_cmd],
            input=bril_texto,
            capture_output=True,
            text=True
        )
        if p1.returncode != 0:
            print(f"[ERRO bril2json]\n{p1.stderr}", file=sys.stderr)
            return

        # Passo 2: brili
        p2 = subprocess.run(
            [brili_cmd],
            input=p1.stdout,
            capture_output=True,
            text=True
        )
        if p2.returncode != 0:
            print(f"[ERRO brili]\n{p2.stderr}", file=sys.stderr)
        else:
            print("[Resultado]")
            print(p2.stdout if p2.stdout else "(sem saída)")

    except Exception as e:
        print(f"[ERRO ao executar] {e}", file=sys.stderr)


# ── Ponto de entrada ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python compilador.py <arquivo.cl> [-o saida.bril] [--no-run]")
        sys.exit(1)

    nome_arquivo = sys.argv[1]
    if not nome_arquivo.endswith(".cl"):
        print(f"[ERRO] Esperado arquivo .cl, recebido: '{nome_arquivo}'")
        sys.exit(1)

    try:
        with open(nome_arquivo, "r", encoding="utf-8") as f:
            codigo = f.read()
    except FileNotFoundError:
        print(f"[ERRO] Arquivo não encontrado: '{nome_arquivo}'")
        sys.exit(1)

    saida    = None
    if "-o" in sys.argv:
        idx = sys.argv.index("-o")
        if idx + 1 < len(sys.argv):
            saida = sys.argv[idx + 1]

    executar = "--no-run" not in sys.argv

    compilar(codigo, saida, executar)
