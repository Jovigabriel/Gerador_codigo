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




def _limpar_bril(codigo: str) -> str:
    """
    Remove da versão completa tudo que não é instrução Bril real:
      - Linhas que são só comentário (#)
      - Linhas com placeholder de string (ptr = const 0  # placeholder)
      - Linhas com aviso de recurso ignorado
      - Linhas em branco extras
    Mantém: assinaturas de função, labels, instruções reais, ret, print, br, jmp.
    """
    linhas_originais = codigo.split("\n")
    linhas_limpas = []

    ignorar_conteudo = [
        "# placeholder string",
        "# out_string ignorado",
        "# in_string não suportado",
        "# in_int não suportado",
        "# isvoid simplificado",
        "# while retorna void",
        "# CASE não suportado",
        "# nó desconhecido",
        "# string literal",
        "ignorado (Bril não suporta",
    ]

    for linha in linhas_originais:
        stripped = linha.strip()

        # Pula linhas que são só comentário
        if stripped.startswith("#"):
            continue

        # Pula linhas que contêm marcadores de recurso não suportado
        if any(marcador in linha for marcador in ignorar_conteudo):
            continue

        linhas_limpas.append(linha)

    # Remove linhas em branco consecutivas (mantém no máximo uma)
    resultado = []
    linha_anterior_vazia = False
    for linha in linhas_limpas:
        if linha.strip() == "":
            if not linha_anterior_vazia:
                resultado.append(linha)
            linha_anterior_vazia = True
        else:
            resultado.append(linha)
            linha_anterior_vazia = False

    return "\n".join(resultado)


def _avisar_recursos_nao_suportados(arvore):
    """
    Percorre a AST e avisa sobre recursos que não são suportados pelo brili:
      - Strings literais
      - out_string / in_string
      - Métodos de String (concat, length, substr)
    """
    avisos = []

    def percorrer(no):
        if no is None:
            return
        if isinstance(no, list):
            for item in no:
                percorrer(item)
            return
        if not isinstance(no, tuple):
            return

        tipo = no[0]

        if tipo == "STRING":
            avisos.append(f"  - String literal na linha {no[1]}: {repr(no[2])}")

        elif tipo == "CHAMADA DE FUNÇÃO":
            nome = no[2][1]
            if nome in ("out_string", "in_string"):
                avisos.append(f"  - Chamada a '{nome}' na linha {no[1]} (I/O de strings não suportado)")

        elif tipo == "CHAMADA DE MÉTODO":
            metodo = no[3][1]
            if metodo in ("concat", "length", "substr"):
                avisos.append(f"  - Método String.{metodo}() na linha {no[1]} (strings não suportadas)")

        elif tipo == "CHAMADA ESTÁTICA":
            metodo = no[4][1]
            if metodo in ("concat", "length", "substr"):
                avisos.append(f"  - Método String.{metodo}() na linha {no[1]} (strings não suportadas)")

        # Continua percorrendo filhos
        for filho in no[1:]:
            percorrer(filho)

    percorrer(arvore)

    if avisos:
        print("\n[AVISO] O programa usa recursos não suportados pelo Bril/brili:", file=sys.stderr)
        print("  Strings e I/O de texto não existem no Bril core.", file=sys.stderr)
        print("  As seguintes ocorrências serão ignoradas na execução:\n", file=sys.stderr)
        for a in avisos:
            print(a, file=sys.stderr)
        print("", file=sys.stderr)


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

    # ── Fase 2.5: Aviso de recursos não suportados ───────────────────────────
    _avisar_recursos_nao_suportados(arvore)

    # ── Fase 3: Geração de código Bril ───────────────────────────────────────
    print("[3/3] Gerando código Bril...", file=sys.stderr)
    gerador = GeradorBril(arvore)
    gerador.gerar()
    codigo_bril = "\n".join(gerador.codigo)
    # print(codigo_bril)

    # ── Salvar em arquivo ─────────────────────────────────────────────────────
    # Sempre salva em saida.bril (versão completa com comentários)
    arquivo_fixo = "saida.bril"
    with open(arquivo_fixo, "w", encoding="utf-8") as f:
        f.write(codigo_bril)
    print(f"[OK] Código Bril salvo em: {arquivo_fixo}", file=sys.stderr)

    # Salva saida_limpa.bril (só instruções reais, sem comentários)
    arquivo_limpo = "saida_limpa.bril"
    codigo_limpo = _limpar_bril(codigo_bril)
    with open(arquivo_limpo, "w", encoding="utf-8") as f:
        f.write(codigo_limpo)
    print(f"[OK] Código Bril limpo salvo em: {arquivo_limpo}", file=sys.stderr)

    if arquivo_saida:
        with open(arquivo_saida, "w", encoding="utf-8") as f:
            f.write(codigo_bril)
        print(f"[OK] Código Bril também salvo em: {arquivo_saida}", file=sys.stderr)

    bril_path = arquivo_limpo   # executa a versão limpa
    deletar_temp = False

    # ── Fase 4: Execução com brili ────────────────────────────────────────────
    if executar:
        _executar_bril(bril_path)



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
