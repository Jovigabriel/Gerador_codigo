import sys
import ply.lex as lex

#Criando uma tupla chamada estados, isso vai servir para os comentarios em bloco e também para as Strings
states = (
    ("comment", "exclusive"),
    ("string" , "exclusive"),   
          )


#Criando um dicionario que irá armazenar as palavras reservadas de cool e o valor será a versão maiuscula dessas palavras

reservadas = {
    'class' : 'CLASS',
    'if': 'IF',
    'else': 'ELSE',
    'fi' : 'FI',
    'case' : 'CASE',
    'loop' : 'LOOP',
    'pool' : 'POOL',
    'esac' : 'ESAC',
    'in': 'IN',
    'while' : 'WHILE',
    'new' : 'NEW',
    'of': 'OF',
    'not': 'NOT',
    'inherits': 'INHERITS',
    'isvoid': 'ISVOID',
    'let': 'LET',
    'then': 'THEN',
}

#Lista de Tokens com esse nome é necessaria, pois a biblioteca usa essa lista para realizar suas funções
tokens = [
    
    #TOKENS DAS PALAVRAS RESERVADAS
    'CLASS',
    'IF',
    'ELSE',
    'FI',
    'CASE',
    'LOOP',
    'POOL',
    'ESAC',
    'IN',
    'WHILE',
    'NEW',
    'OF',
    'NOT',
    'INHERITS',
    'ISVOID',
    'LET',
    'THEN',

    #tokens para identificadores

    'TYPEID',
    'OBJECTID',
    'INT_CONST',
    'STR_CONST',
    'BOOL_CONST', #na linguagem cool true e false obrigatoriamente precisam começar com letra maiuscula, o restante pode ser minusculo ou maiuscula

    #Operadores
    'LE',
    'ASSIGN', #ATRIBUIÇÃO EM COOL <-
    'DARROW', #=>
    'PLUS',
    'MINUS',
    'MULT',
    'DIV',
    'LBRACE',
    'RBRACE',
    'LPAREN',
    'RPAREN',
    'COLON',
    'SEMI',
    'DOT',
    'COMMA',
    'LESS',
    'EQUAL',
    'TILDE', #TIL ~ , EM COOL o til é usado para dizer que um número negativo, o sinal de menos serve somente para a operação de menos
    'AT' #ARROBA @, serve para chamar metodo do pai de um objeto
]


# Nessa etapa temos que adicionar nas variaveis que o PLY oferece os respectivos simbolos que irão representar os tokens acima

#Ordem de tamanho parece ser importante, os maiores precisam ficar antes dos menores, para evitar que um token seja criado antes do tempo

# O nome precisa sempre começar com t_ e o restante tem que ser escrito examtamente igual a como estar na lista dos tokens
t_DARROW = r'=>'
t_ASSIGN =  r'<-'
t_LE = r'<='
t_PLUS= r'\+' #A contrabarra serve para que fique claro que queremos a expressão literal e não o sentido que o regex impoe
t_MINUS = r'-'
t_MULT = r'\*'
t_DIV    = r'/'
t_LESS   = r'<'
t_EQUAL  = r'='
t_TILDE  = r'~'
t_AT     = r'@'
t_LBRACE = r'\{'   
t_RBRACE = r'\}'  
t_LPAREN = r'\('   
t_RPAREN = r'\)'   
t_COLON  = r':'
t_SEMI   = r';'
t_DOT    = r'\.'   
t_COMMA  = r','
t_ignore = ' \t' #ignora espaços em branco e tabs
t_comment_ignore = ''
t_string_ignore = ''
#Essas duas ultimas variaveis são para os outros estados do ply, elas não ignoram nada, mas são obrigatoria


#Agora temos que criar funções para identificar tokens que não seguem o mesmo padrão dos anteriores

#LEMBRETE IMPORTATE cool é Case insensitive, então se eu escrever as palavras chaves maiusculas, minusculas ou misturado, tanto faz para ele, só não podemos fazer isso para true e false, pois suas primeiras letras precisam ser minusculas


def t_INT_CONST(t):
    r'\d+'
    t.value = int(t.value) #transformando a string númerica em int 
    return t

def t_TYPEID(t): #TYPE ID obrigatoriamente começa com letras maiusculas
    r'[A-Z][A-Za-z0-9_]*'
    #Verificando se as letras lidas formam alguma palavra reservada, se não formar, type vai ser TYPE_ID
    palavra = t.value.lower()
    t.type = reservadas.get(palavra, "TYPEID")
    return t


def t_OBJECTID(t): #OBJECT ID obrigatoriamente começa com letras MINUSCULAS
    r'[a-z][A-Za-z0-9_]*'
    palavra = t.value.lower()
    #Verificando se a palavra formada é true ou false, pois se forem, serão do tipo Bool_Const
    if palavra == 'true':
        t.type  = 'BOOL_CONST'
        t.value = True
    elif palavra == 'false':
        t.type  = 'BOOL_CONST'
        t.value = False
    else: #Verificando se as letras lidas formam alguma palavra reservada, se não formar, type vai ser OBJECTID_ID
        t.type = reservadas.get(palavra, 'OBJECTID')
    return t




def t_newline(t):
    r'\n+'  #Vendo se existe quebra de linhas
    # t.lexer.lineno é o contador de linhas do ply
    t.lexer.lineno += len(t.value) #Adicionando no contador de linhas a quantidade de quebras de linhas
    pass #NÃO RETORNA NADA


def t_error(t):
    print(f"Caractere inválido {t.value[0]} na linha {t.lexer.lineno}")
    t.lexer.skip(1) #Pula para o proximo caracter


def t_COMMENT_LINE(t):
    r'--.*' #Em regex, o ponto (.) significa que podemos receber QUALQUER coisa, só não dá para reconhecer \n
    pass #Vai ignorar o bloco de comentarios inteiro

#Tratando Strings

def t_start_string(t):
    r'\"'
    t.lexer.string_buf = "" #eSSE BUF VAI ARMAZENAR A STRING QUE ESTA SENDO FROMADA
    t.lexer.begin('string') #INDO PARA O ESTADO DE STRING

def t_string_fechar(t):
    r'\"'
    t.value =  t.lexer.string_buf #quando a string fecha eu adiciono a palavra formada no buffer no t.value
    t.type = 'STR_CONST'
    t.lexer.begin('INITIAL')
    return t

def t_string_chars(t):
    #regex: \\.  |  [^\"\\\n]+ , reconhece  \ e qualquer letra que venha depois, também  reconhece qualquer coisa que não seja contra-barra, aspas ou quebra de linha
    #  o primeiro caso espera realmente que seja escrito \n, o segundo não aceita que o enter seja pressionado, gerando um outrro tipo de \n
    r'\\.|[^\"\\\n]+'

    if t.value.startswith('\\'): #verificando se estamos no caso 1
        char = t.value[1]
        tabela = { #tabela de escapes validos em cool
            'n':  '\n',
            't':  '\t',
            '\\': '\\',
            '"':  '"',
            'b':  '\b',
            'f':  '\f',
        }
        # se não conhecer o escape, vai usar o próprio char, por exemplo \z vai ser só z
        t.lexer.string_buf += tabela.get(char, char)
    else:
        # caractere normal, adiciona direto
        t.lexer.string_buf += t.value


def t_string_newline(t):
    r'\n+'
    print(f"Erro: String não fechada na linha {t.lexer.lineno}")
    t.lexer.lineno += len(t.value)
    t.lexer.begin('INITIAL')

def t_string_error(t): 
        t.lexer.skip(1)

#Tratando comentários de bloco

def t_start_comment(t):
    r'\(\*'
    t.lexer.comment_level = 1
    t.lexer.begin('comment')

def t_comment_abrir(t):
    r'\(\*'
    t.lexer.comment_level +=1

def t_comment_fechar(t):
    r'\*\)'
    t.lexer.comment_level -= 1

    if t.lexer.comment_level == 0:
        t.lexer.begin('INITIAL')

def t_comment_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value) 
    pass 

def t_comment_chars(t):
    r'[^\(\*\n]+' # Consome tudo que não seja (, *, ) ou quebra de linha de uma vez
    pass          

def t_comment_error(t):
    t.lexer.skip(1)


#EXECUTANDO LEXER

lexer = lex.lex()

if __name__ == '__main__':

    #Verificando arquivo passado por parametro
    if len(sys.argv)> 1:
        nome_arquivo = sys.argv[1]

        if not nome_arquivo.endswith('.cl'):
            print(f'ERRO: Arquivo recebido não é do tipo .cl')
            sys.exit(1)

        print(f'LENDO O SEGUINTE ARQUIVO: {nome_arquivo}')
        try:
            with open(nome_arquivo, 'r') as arq:
                dados = arq.read()
                lexer.input(dados)
        except FileNotFoundError:
            print(f"Arquivo {nome_arquivo} não encontrado")
            sys.exit(1)

    #Gerando tokens
    while True:
        tok = lexer.token()
        if not tok:
            break
        print(tok)