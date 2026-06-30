"""
gerador.py — Gerador de código Bril a partir da AST Cool
=========================================================
Estrutura real dos nós (com linha sempre no índice 1):

  ("INTEIRO",          linha, valor)
  ("BOOLEANO",         linha, valor)
  ("STRING",           linha, valor)
  ("VARIAVEL",         linha, nome)
  ("NEW",              linha, tipo)
  ("ATRIBUIÇÃO",       linha, nome_var, expr)
  ("SOMA",             linha, esq, dir)
  ("SUBTRAÇÃO",        linha, esq, dir)
  ("MULTIPLICAÇÃO",    linha, esq, dir)
  ("DIVISÃO",          linha, esq, dir)
  ("MENOR QUE",        linha, esq, dir)
  ("MENOR OU IGUAL",   linha, esq, dir)
  ("IGUAL",            linha, esq, dir)
  ("NÃO LÓGICO",       linha, expr)
  ("NEGAÇÃO NUMÉRICA", linha, expr)
  ("ISVOID",           linha, expr)
  ("BLOCO",            linha, [lista_exprs])
  ("IF",               linha, ("CONDIÇÃO", expr), ("VERDADE", expr), ("ELSE", expr))
  ("WHILE",            linha, ("CONDIÇÃO", expr), ("CORPO", expr))
  ("LET",              linha, ("VARIÁVEIS", [decls]), ("CORPO", expr))
  ("CASE",             linha, ("EXPRESSÃO", expr), ("CASOS", [ramos]))
  ("CHAMADA DE FUNÇÃO",linha, ("NOME", nome), ("PARÂMETROS", [args]))
  ("CHAMADA DE MÉTODO",linha, ("OBJETO", expr), ("MÉTODO", nome), ("PARÂMETROS", [args]))
  ("CHAMADA ESTÁTICA", linha, ("OBJETO", expr), ("CLASSE MÃE", tipo), ("MÉTODO", nome), ("PARÂMETROS", [args]))
  ("DECLARAÇÃO LET",   linha, ("NOME", nome), ("TIPO", tipo))
  ("DECLARAÇÃO LET",   linha, ("NOME", nome), ("TIPO", tipo), ("VALOR", expr))
  ("RAMO CASE",        linha, ("NOME", nome), ("TIPO", tipo), ("EXECUTA", expr))
"""

from __future__ import annotations
from typing import Optional


class GeradorBril:

    def __init__(self, arvore):
        self.arvore = arvore
        self._temp_count  = 0
        self._label_count = 0
        self._linhas: list[str] = []
        self.codigo: list[str] = []
        self._tipo_var: dict[str, str] = {}
        self._classe_atual: str = ""

    # ── utilidades ──────────────────────────────────────────────────────────

    def _novo_temp(self, tipo: str = "int") -> str:
        self._temp_count += 1
        nome = f"t{self._temp_count}"
        self._tipo_var[nome] = tipo
        return nome

    def _novo_label(self) -> str:
        """Retorna nome sem ponto. Use _ldecl() e _lref() ao emitir."""
        self._label_count += 1
        return f"lbl{self._label_count}"

    def _ldecl(self, lbl: str) -> str:
        """Declaração de label: .lbl1:"""
        return f".{lbl}:"

    def _lref(self, lbl: str) -> str:
        """Referência em br/jmp: .lbl1"""
        return f".{lbl}"

    def _label_decl(self, lbl: str) -> str:
        """Emite declaração de label no formato .lbl1:"""
        return f"{lbl}:"

    def _label_ref(self, lbl: str) -> str:
        """Referência a label em br/jmp: .lbl1"""
        return lbl

    def _emit(self, linha: str):
        self._linhas.append(linha)

    def _tipo_bril(self, tipo_cool: str) -> str:
        return {
            "Int":       "int",
            "Bool":      "bool",
            "String":    "ptr",
            "Object":    "ptr",
            "SELF_TYPE": "ptr",
        }.get(tipo_cool, "ptr")

    # ── ponto de entrada ────────────────────────────────────────────────────

    def gerar(self):
        """Percorre a AST e popula self.codigo. Não imprime nada."""
        assert self.arvore[0] == "PROGRAMA", "Raiz inválida"
        for classe in self.arvore[1]:
            self._gerar_classe(classe)

    def _gerar_classe(self, no_classe):
        # ("CLASSE", linha, nome, heranca, ("FEATURES", [...]))
        self._classe_atual = no_classe[2]
        for feat in no_classe[4][1]:
            if feat[0] == "FUNÇÃO":
                self._gerar_funcao(feat)

    def _gerar_funcao(self, no_func):
        # ("FUNÇÃO", linha, nome, ("PARAMETROS",[...]), ("TIPO", tipo), ("CORPO", expr))
        _, _linha, nome_metodo, no_params, no_tipo, no_corpo = no_func

        self._temp_count  = 0
        self._label_count = 0
        self._linhas      = []
        self._tipo_var    = {}

        params   = no_params[1]
        tipo_ret = self._tipo_bril(no_tipo[1])

        partes_sig = []
        for p in params:
            # ("PARAMETRO", nome, ("TIPO", tipo))
            pnome = p[1]
            ptipo = self._tipo_bril(p[2][1])
            self._tipo_var[pnome] = ptipo
            partes_sig.append(f"{pnome}:{ptipo}")

        # brili exige @main como ponto de entrada (Main.main -> @main)
        if self._classe_atual == "Main" and nome_metodo == "main":
            nome_func = "main"
        else:
            nome_func = f"{self._classe_atual}_{nome_metodo}"

        sig = f"@{nome_func}({', '.join(partes_sig)}): {tipo_ret}"

        self._emit(sig + " {")

        resultado = self._gerar_expr(no_corpo[1])

        # No @main, imprime o resultado antes de retornar
        # (brili não exibe o valor de ret automaticamente — precisa de print)
        if nome_func == "main" and resultado:
            self._emit(f"  print {resultado};")

        if resultado:
            self._emit(f"  ret {resultado};")
        else:
            self._emit(f"  ret;")

        self._emit("}")
        self._emit("")
        self.codigo.extend(self._linhas)

    # ── despachante principal ────────────────────────────────────────────────

    def _gerar_expr(self, no) -> Optional[str]:
        if no is None:
            return None

        tipo = no[0]

        if tipo == "INTEIRO":           return self._gen_const_int(no)
        if tipo == "BOOLEANO":          return self._gen_const_bool(no)
        if tipo == "STRING":            return self._gen_const_string(no)
        if tipo == "VARIAVEL":          return self._gen_variavel(no)
        if tipo == "NEW":               return self._gen_new(no)
        if tipo == "ATRIBUIÇÃO":        return self._gen_atribuicao(no)
        if tipo == "BLOCO":             return self._gen_bloco(no)
        if tipo == "IF":                return self._gen_if(no)
        if tipo == "WHILE":             return self._gen_while(no)
        if tipo == "LET":               return self._gen_let(no)
        if tipo == "NÃO LÓGICO":        return self._gen_nao_logico(no)
        if tipo == "NEGAÇÃO NUMÉRICA":  return self._gen_negacao_numerica(no)
        if tipo == "ISVOID":            return self._gen_isvoid(no)
        if tipo == "CHAMADA DE FUNÇÃO": return self._gen_chamada_funcao(no)
        if tipo in ("CHAMADA DE MÉTODO", "CHAMADA ESTÁTICA"):
                                        return self._gen_chamada_metodo(no)
        if tipo in ("SOMA", "SUBTRAÇÃO", "MULTIPLICAÇÃO", "DIVISÃO"):
                                        return self._gen_aritmetica(no)
        if tipo in ("MENOR QUE", "MENOR OU IGUAL", "IGUAL"):
                                        return self._gen_comparacao(no)
        if tipo == "CASE":
            self._emit(f"  # CASE não suportado — ignorado")
            return None

        self._emit(f"  # nó desconhecido: {tipo}")
        return None

    # ── literais ────────────────────────────────────────────────────────────

    def _gen_const_int(self, no) -> str:
        # ("INTEIRO", linha, valor)
        valor = no[2]
        t = self._novo_temp("int")
        self._emit(f"  {t}: int = const {valor};")
        return t

    def _gen_const_bool(self, no) -> str:
        # ("BOOLEANO", linha, valor)
        valor = no[2]
        bril_val = "true" if valor is True or str(valor).lower() == "true" else "false"
        t = self._novo_temp("bool")
        self._emit(f"  {t}: bool = const {bril_val};")
        return t

    def _gen_const_string(self, no) -> str:
        # ("STRING", linha, valor)
        valor = no[2]
        self._emit(f"  # string literal: {repr(valor)}")
        t = self._novo_temp("ptr")
        self._emit(f"  {t}: ptr = const 0;  # placeholder string")
        return t

    def _gen_variavel(self, no) -> str:
        # ("VARIAVEL", linha, nome)
        return no[2]

    # ── aritmética e comparações ─────────────────────────────────────────────

    _OP_ARIT = {
        "SOMA":          ("add", "int"),
        "SUBTRAÇÃO":     ("sub", "int"),
        "MULTIPLICAÇÃO": ("mul", "int"),
        "DIVISÃO":       ("div", "int"),
    }
    _OP_CMP = {
        "MENOR QUE":      ("lt",  "bool"),
        "MENOR OU IGUAL": ("le",  "bool"),
        "IGUAL":          ("eq",  "bool"),
    }

    def _gen_aritmetica(self, no) -> str:
        # ("SOMA", linha, esq, dir)
        op_bril, tipo = self._OP_ARIT[no[0]]
        esq  = self._gerar_expr(no[2])
        dir_ = self._gerar_expr(no[3])
        t = self._novo_temp(tipo)
        self._emit(f"  {t}: {tipo} = {op_bril} {esq} {dir_};")
        return t

    def _gen_comparacao(self, no) -> str:
        # ("MENOR QUE", linha, esq, dir)
        op_bril, tipo = self._OP_CMP[no[0]]
        esq  = self._gerar_expr(no[2])
        dir_ = self._gerar_expr(no[3])
        t = self._novo_temp(tipo)
        self._emit(f"  {t}: {tipo} = {op_bril} {esq} {dir_};")
        return t

    def _gen_nao_logico(self, no) -> str:
        # ("NÃO LÓGICO", linha, expr)
        operando = self._gerar_expr(no[2])
        t = self._novo_temp("bool")
        self._emit(f"  {t}: bool = not {operando};")
        return t

    def _gen_negacao_numerica(self, no) -> str:
        # ("NEGAÇÃO NUMÉRICA", linha, expr)
        operando = self._gerar_expr(no[2])
        zero = self._novo_temp("int")
        self._emit(f"  {zero}: int = const 0;")
        t = self._novo_temp("int")
        self._emit(f"  {t}: int = sub {zero} {operando};")
        return t

    def _gen_isvoid(self, no) -> str:
        # ("ISVOID", linha, expr)
        self._gerar_expr(no[2])
        t = self._novo_temp("bool")
        self._emit(f"  {t}: bool = const false;  # isvoid simplificado")
        return t

    # ── bloco, atribuição, let ───────────────────────────────────────────────

    def _gen_bloco(self, no) -> Optional[str]:
        # ("BLOCO", linha, [lista_exprs])
        resultado = None
        for expr in no[2]:
            resultado = self._gerar_expr(expr)
        return resultado

    def _gen_atribuicao(self, no) -> str:
        # ("ATRIBUIÇÃO", linha, nome_var, expr_valor)
        nome_var = no[2]
        resultado = self._gerar_expr(no[3])
        tipo = self._tipo_var.get(resultado, "int")
        self._tipo_var[nome_var] = tipo
        self._emit(f"  {nome_var}: {tipo} = id {resultado};")
        return nome_var

    def _gen_let(self, no) -> Optional[str]:
        # ("LET", linha, ("VARIÁVEIS", [decls]), ("CORPO", expr))
        decls = no[2][1]
        corpo = no[3][1]

        for decl in decls:
            # ("DECLARAÇÃO LET", linha, ("NOME", nome), ("TIPO", tipo) [, ("VALOR", expr)])
            nome_var  = decl[2][1]
            tipo_cool = decl[3][1]
            tipo_bril = self._tipo_bril(tipo_cool)
            self._tipo_var[nome_var] = tipo_bril

            if len(decl) == 5:
                # tem valor inicial — ("VALOR", expr) está em decl[4]
                val_temp = self._gerar_expr(decl[4][1])
                self._emit(f"  {nome_var}: {tipo_bril} = id {val_temp};")
            else:
                # valor padrão por tipo
                if tipo_bril == "int":
                    self._emit(f"  {nome_var}: int = const 0;")
                elif tipo_bril == "bool":
                    self._emit(f"  {nome_var}: bool = const false;")
                else:
                    self._emit(f"  {nome_var}: ptr = const 0;")

        return self._gerar_expr(corpo)

    # ── if e while ──────────────────────────────────────────────────────────

    def _gen_if(self, no) -> str:
        # ("IF", linha, ("CONDIÇÃO", expr), ("VERDADE", expr), ("ELSE", expr))
        expr_cond = no[2][1]
        expr_then = no[3][1]
        expr_else = no[4][1]

        lbl_then = self._novo_label()
        lbl_else = self._novo_label()
        lbl_fim  = self._novo_label()

        cond_var = self._gerar_expr(expr_cond)
        self._emit(f"  br {cond_var} .{lbl_then} .{lbl_else};")

        t_resultado = self._novo_temp("int")

        self._emit(f".{lbl_then}:")
        then_res = self._gerar_expr(expr_then)
        if then_res:
            tipo = self._tipo_var.get(then_res, "int")
            self._tipo_var[t_resultado] = tipo
            self._emit(f"  {t_resultado}: {tipo} = id {then_res};")
        self._emit(f"  jmp .{lbl_fim};")

        self._emit(f".{lbl_else}:")
        else_res = self._gerar_expr(expr_else)
        if else_res:
            tipo = self._tipo_var.get(else_res, "int")
            self._emit(f"  {t_resultado}: {tipo} = id {else_res};")
        self._emit(f"  jmp .{lbl_fim};")

        self._emit(f".{lbl_fim}:")
        return t_resultado

    def _gen_while(self, no) -> str:
        # ("WHILE", linha, ("CONDIÇÃO", expr), ("CORPO", expr))
        expr_cond  = no[2][1]
        expr_corpo = no[3][1]

        lbl_inicio = self._novo_label()
        lbl_corpo  = self._novo_label()
        lbl_fim    = self._novo_label()

        self._emit(f".{lbl_inicio}:")
        cond_var = self._gerar_expr(expr_cond)
        self._emit(f"  br {cond_var} .{lbl_corpo} .{lbl_fim};")

        self._emit(f".{lbl_corpo}:")
        self._gerar_expr(expr_corpo)
        self._emit(f"  jmp .{lbl_inicio};")

        self._emit(f".{lbl_fim}:")
        t = self._novo_temp("ptr")
        self._emit(f"  {t}: ptr = const 0;  # while retorna void")
        return t

    # ── chamadas ────────────────────────────────────────────────────────────

    def _gen_chamada_funcao(self, no) -> Optional[str]:
        # ("CHAMADA DE FUNÇÃO", linha, ("NOME", nome), ("PARÂMETROS", [args]))
        nome_metodo = no[2][1]
        args        = no[3][1]
        args_vars   = [self._gerar_expr(a) for a in args]

        if nome_metodo == "out_string":
            self._emit(f"  # out_string({args_vars[0] if args_vars else ''})")
            if args_vars:
                self._emit(f"  call @print_str {args_vars[0]};")
            t = self._novo_temp("ptr")
            self._emit(f"  {t}: ptr = const 0;")
            return t

        if nome_metodo == "out_int":
            self._emit(f"  # out_int({args_vars[0] if args_vars else ''})")
            if args_vars:
                self._emit(f"  call @print_int {args_vars[0]};")
            t = self._novo_temp("ptr")
            self._emit(f"  {t}: ptr = const 0;")
            return t

        if nome_metodo == "in_int":
            t = self._novo_temp("int")
            self._emit(f"  {t}: int = call @read_int;")
            return t

        if nome_metodo == "in_string":
            t = self._novo_temp("ptr")
            self._emit(f"  {t}: ptr = call @read_str;")
            return t

        if self._classe_atual == "Main" and nome_metodo == "main":
            nome_func = "main"
        else:
            nome_func = f"{self._classe_atual}_{nome_metodo}"
        return self._emitir_call(nome_func, args_vars, "int")

    def _gen_chamada_metodo(self, no) -> Optional[str]:
        # ("CHAMADA DE MÉTODO", linha, ("OBJETO",expr), ("MÉTODO",nome), ("PARÂMETROS",[args]))
        # ("CHAMADA ESTÁTICA",  linha, ("OBJETO",expr), ("CLASSE MÃE",tipo), ("MÉTODO",nome), ("PARÂMETROS",[args]))
        is_estatica = (no[0] == "CHAMADA ESTÁTICA")
        obj_var = self._gerar_expr(no[2][1])

        if is_estatica:
            classe_alvo = no[3][1]
            nome_metodo = no[4][1]
            args        = no[5][1]
        else:
            classe_alvo = self._classe_atual
            nome_metodo = no[3][1]
            args        = no[4][1]

        if nome_metodo in ("out_string", "out_int", "in_int", "in_string"):
            return self._gen_chamada_funcao(
                ("CHAMADA DE FUNÇÃO", no[1],
                 ("NOME", nome_metodo),
                 ("PARÂMETROS", args))
            )

        args_vars = [obj_var] + [self._gerar_expr(a) for a in args]
        nome_func = f"{classe_alvo}_{nome_metodo}"
        return self._emitir_call(nome_func, args_vars, "int")

    def _emitir_call(self, nome_func: str, args_vars: list, tipo_ret: str) -> str:
        t = self._novo_temp(tipo_ret)
        args_str = " ".join(v for v in args_vars if v)
        self._emit(f"  {t}: {tipo_ret} = call @{nome_func} {args_str};")
        return t

    # ── new ─────────────────────────────────────────────────────────────────

    def _gen_new(self, no) -> str:
        # ("NEW", linha, tipo)
        tipo_cool = no[2]
        t = self._novo_temp("ptr")
        self._emit(f"  {t}: ptr = call @{tipo_cool}_new;  # new {tipo_cool}")
        return t


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 2:
        try:
            from lexico import lexer
            from parser import parser as cool_parser
            codigo = open(sys.argv[1]).read()
            arvore = cool_parser.parse(codigo, lexer=lexer.clone())
        except ImportError:
            print("lexico/parser não encontrados", file=sys.stderr)
            sys.exit(1)
        gerador = GeradorBril(arvore)
        gerador.gerar()
