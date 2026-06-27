import sys
from lexico import lexer
from parser import parser


#Descreve um metodo de uma classe, vai armazenar coisas como o retorno e os tipos dos parametros
class MetodoDescritor:
    def __init__(self, tipo_retorno, tipo_parametro=None): #se não tiver parametro, tipo_parametro recebe none
        self.tipo_retorno = tipo_retorno
        if tipo_parametro is None:
            self.tipo_parametro = []
        else:
            self.tipo_parametro = tipo_parametro #já é uma lista

    #Formatação para quando for imprimir
    def __repr__(self):
        return f"Parametros: {self.tipo_parametro} /// Retorno: {self.tipo_retorno}"


# Serve para descrever e armazenas as classes que são criadas, vai armazenar dados como nome, nome da mae, atributos, metodos
class ClasseDescritor:
    def __init__(self, nome, nome_mae=None):
        self.nome = nome
        self.nome_mae = nome_mae
        self.atributos = {} #tanto atributo, quanto metodo vão ser dicionanarios. atributo tem como chave o nome do atributo e o valor vai ser o tipo do atributo
        self.metodos = {}   #metodo tem como chave o seu nome e o valor é uma instancia do MetodoDescritor

    def __repr__(self):
        return f"Classe {self.nome} (Herda de {self.nome_mae})"


#Classe do analisador semantico, é a principal do nosso codigo, vai fazer o rabalho
class AnalisadorSemantico:

    #Criando as variaveis da classe e recebendo a arvore
    def __init__(self, arvore_sintatica):
        self.arvore = arvore_sintatica
        self.tabela_classes = {} #Vai receber instancias de ClasseDescrito
        self.escopo_atual = [] #Pilha de escopos, começa vazia
        self.inicializar_classes_basicas()

    #Função para quando achar um erro imprimir mensagem e encerrar execução
    def reportar_erro(self, mensagem):
        print(mensagem)
        sys.exit(1)

    #metodo para inicializar as classes pre existentes em cool, como int, bool, string, io, object. também incluimos os metodos que já existem neles
    def inicializar_classes_basicas(self):
        # Object
        obj = ClasseDescritor("Object") #Criei uma classe
        obj.metodos["abort"] = MetodoDescritor("Object") #Adicionando os metodos
        obj.metodos["type_name"] = MetodoDescritor("String")
        obj.metodos["copy"] = MetodoDescritor("SELF_TYPE") #SELF_TYPE = mesmo tipo da classe
        self.tabela_classes["Object"] = obj #inserindo classe na tabela de classes

        # IO
        io = ClasseDescritor("IO", "Object") #herda de object
        io.metodos["out_string"] = MetodoDescritor("SELF_TYPE", ["String"])
        io.metodos["out_int"] = MetodoDescritor("SELF_TYPE", ["Int"])
        io.metodos["in_string"] = MetodoDescritor("String")
        io.metodos["in_int"] = MetodoDescritor("Int")
        self.tabela_classes["IO"] = io

        # Int, String, Bool
        self.tabela_classes["Int"] = ClasseDescritor("Int", "Object")
        str_class = ClasseDescritor("String", "Object")
        str_class.metodos["length"] = MetodoDescritor("Int")
        str_class.metodos["concat"] = MetodoDescritor("String", ["String"])
        str_class.metodos["substr"] = MetodoDescritor("String", ["Int", "Int"])
        self.tabela_classes["String"] = str_class
        self.tabela_classes["Bool"] = ClasseDescritor("Bool", "Object")

    #essa função basicamente faz o funccionameno acontecer na ordem certa, ela registras todas as classes do programa e depois chama a função para verificar se os tipos estão corretos
    def analisar(self):

        #verificando se primeiro ramo da arvore é programa
        if self.arvore and self.arvore[0] == "PROGRAMA":
            lista_classes = self.arvore[1]
            
            # Passagem 1: Coleta de Assinaturas e Herança
            for classe in lista_classes:
                self.registrar_classe(classe)
            print(f"Classes registradas: {list(self.tabela_classes.keys())}\n")
            
            #verifica existencia da main
            self.validar_main()
            
            # Passagem 2: Checagem do corpo dos métodos
            self.checar_tipos(lista_classes)
        else:
            self.reportar_erro("[ERRO SEMÂNTICO] Estrutura do programa inválida.")

    #Função para registrar uma classe
    def registrar_classe(self, classe):
        #o claase é o ramo da arvore do jeito que construimos no parser, para lembrar da estrutura temos que olhar o arquivo do parser
        linha_classe = classe[1] 
        nome = classe[2] 
        heranca = classe[3]

        #Se não tiver herança, faz herdar de Object, porque toda classe herda de object
        if heranca[0] == "SEM HERANÇA":
            nome_mae = "Object"
        else:
            nome_mae = heranca[1]

        # Se nome for igual os da classe proibidas gera erro
        if nome in ["Object", "Int", "String", "Bool", "IO", "SELF_TYPE"]:
            self.reportar_erro(f"[ERRO SEMANTICO] (Linha {linha_classe}) Tentativa de redefinir classe básica: {nome}")
            
        # Se nome for igual a um nome já existente na tabela de classes, entao gera erro
        if nome in self.tabela_classes:
            self.reportar_erro(f"[ERRO SEMANTICO] (Linha {linha_classe}) Classe '{nome}' já existente.")

        #se nome da mae nao tiver na tabela de classes, gera erro
        if nome_mae not in self.tabela_classes:
            self.reportar_erro(f"[ERRO SEMANTICO] (Linha {linha_classe}) Herança de classe inexistente: '{nome_mae}'.")

        #Se nome da mae for int, string ou bool gera erro
        if nome_mae in ["Int", "String", "Bool"]:
            self.reportar_erro(f"[ERRO SEMANTICO] (Linha {linha_classe}) Herança de classe proibida: '{nome_mae}'.")

        #se passa dos testes de proibições então podemos criar uma instancia
        nova_classe = ClasseDescritor(nome, nome_mae)
        mae_descritor = self.tabela_classes[nome_mae]
        #to passando os atributso e metodos da classe mae para a classe filho
        nova_classe.metodos = mae_descritor.metodos.copy()
        
        #Agora a gente começa a analisar realmente o que tem dentro da classe
        lista_features = classe[4][1]
        
        for feature in lista_features:
            linha_feature = feature[1]

            #analisando qual é o feature

            if feature[0] == "ATRIBUTO": 
                nome_atributo = feature[2]
                tipo_atributo = feature[3][1]

                #Atributo não pode ter o nome de self
                if nome_atributo == "self":
                    self.reportar_erro(f"[ERRO SEMANTICO] (Linha {linha_feature}) Nome de atributo 'self' inválido.")
                
                #Tentativa de redefinir um atributo existente, não pode
                if nome_atributo in nova_classe.atributos:
                    self.reportar_erro(f"[ERRO SEMANTICO] (Linha {linha_feature}) Atributo '{nome_atributo}' redefinido.")
                
                #adicionando atributo da classe
                nova_classe.atributos[nome_atributo] = tipo_atributo

            elif feature[0] == "FUNÇÃO":
                nome_metodo = feature[2]
                lista_parametros = feature[3][1]
                tipo_retorno_metodo = feature[4][1]

                for param in lista_parametros:
                    #não pode ter parametro self
                    if param[1] == "self":
                        self.reportar_erro(f"[ERRO SEMANTICO] (Linha {feature[1]}) Parâmetro 'self' inválido no método '{nome_metodo}'.")
                
                #pegando a lista de TIPOS de parametros do metodo
                tipo_parametros = [i[2][1] for i in lista_parametros]
                #criando metodo
                novo_metodo = MetodoDescritor(tipo_retorno_metodo, tipo_parametros)

                #se o metodo ja estiver na tabela de metodo da classe nova, então temos que verificar se ela segue os padroes da classe mae, porque ela é uma reescrita
                if nome_metodo in nova_classe.metodos:
                    metodo_antigo = nova_classe.metodos[nome_metodo]
                    if (metodo_antigo.tipo_retorno != novo_metodo.tipo_retorno) or (metodo_antigo.tipo_parametro != novo_metodo.tipo_parametro):
                        self.reportar_erro(f"[ERRO SEMANTICO] (Linha {linha_feature}) Método '{nome_metodo}' com assinatura diferente da mãe.")

                #adicionando novo metodo
                nova_classe.metodos[nome_metodo] = novo_metodo
            
        #adicionando classe na tabela de classe
        self.tabela_classes[nome] = nova_classe

   #serve para verificar ser a main existe, cool obriga a main existir
    def validar_main(self):
        if "Main" not in self.tabela_classes:
            self.reportar_erro("[ERRO SEMANTICO] O programa precisa ter uma classe 'Main'.")
            
        classe_main = self.tabela_classes["Main"]
        
        if "main" not in classe_main.metodos:
            self.reportar_erro("[ERRO SEMANTICO] A classe 'Main' precisa ter um método 'main'.")
            
        metodo_main = classe_main.metodos["main"]
        
        if len(metodo_main.tipo_parametro) > 0:
            self.reportar_erro("[ERRO SEMANTICO] O método 'main' da classe 'Main' não deve receber parâmetros.")

    
   
    # REFRAS DE ESCOPO E TIPO

    #eSSAS PRIMEIRAS  funções servem para entrar, sair, adicionar ou buscar variavel em um escopo. Nós estamos usando uma pilha para fazer o controle do escopo

    def entrar_escopo(self):
        self.escopo_atual.append({})

    def sair_escopo(self):
        self.escopo_atual.pop()

    #Adicionamos a variavel no elemento do topo da pilha
    def adicionar_variavel(self, nome, tipo):
        dicionario = self.escopo_atual[-1]
        dicionario[nome] = tipo

    #Essa função vai tentar buscar um uma variavel na pilha, para fazer isso, ela vai começar a busca do topo para base, se achar a variavel retorna o tipo
    def buscar_variavel(self, nome, nome_classe_atual):
        for escopo in reversed(self.escopo_atual):
            if nome in escopo:
                return escopo[nome]
        #se a palavra procurada for self, el vai retornar self_type
        if nome == "self":
            return "SELF_TYPE"
        
        #Pegando dados da classe, pois se não achou na pilha, vai olhar atributos da classe
        classe_descritor = self.tabela_classes.get(nome_classe_atual)
        if classe_descritor and nome in classe_descritor.atributos:
            return classe_descritor.atributos[nome]
        #Não achou, então vai retornar None
        return None

    #Esse metodo serve para lidar com polimorfismo, ou seja podemos guardar uma classe filho em uma variavel que seja do tipo dos seus antecessores
    def conforma(self, tipo_real, tipo_esperado): 
        #Se for exatamente o mesmo tipo, ou se o esperado for um Object genérico, então podemos retornar true
        if tipo_real == tipo_esperado or tipo_esperado == "Object":
            return True
            
        #  Se o tipo que esta tentando ser armazenado não existe na tabela
        if tipo_real not in self.tabela_classes:
            return False
            
        # Vou acessando a mãe do tipo_real para ver se acho alguma conexão de hierarquia
        atual = tipo_real
        while atual != "Object" and atual is not None:
            descritor = self.tabela_classes.get(atual)
            if not descritor: break
            
            atual = descritor.nome_mae
            if atual == tipo_esperado: 
                return True
                
        return False

    #iMPLEMENTANDO O LEAST UPPER BOUND, vamos achar o ancestral comum mais proximo para retornar em casos de if e cases
    def juncao_tipos(self, tipo1, tipo2):
        #comparação basica para ver se os tipos são iguais, se for, retorna
        if tipo1 == tipo2: 
            return tipo1
        #vamos criar um caminho com todos os ancestrais do tipo1
        caminho_tipo1 = [tipo1]
        atual = tipo1
        #subindo até chegar em object que é o pai de todos
        while atual != "Object":
            desc = self.tabela_classes.get(atual)
            #se desc for none ou a mae ser none vai fazer o while quebrar
            if not desc or not desc.nome_mae:
                caminho_tipo1.append("Object")
                break
            atual = desc.nome_mae
            #adicionando no caminho
            caminho_tipo1.append(atual)
            
        atual = tipo2
        #agora a gente começa a comparar o tipo2 e seus ancestrais com o caminho que fizemos
        while atual is not None:
            if atual in caminho_tipo1: 
                return atual
            desc = self.tabela_classes.get(atual)
            if not desc: 
                break
            atual = desc.nome_mae
        #no pior dos casos o ancestral comum mais proximo vai ser object
        return "Object"

    #VERIFICA OS TIPOS DOS METODOS E ATRIBUTOSP
    def checar_tipos(self, lista_classes):
        #navegando pelas classes
        for classe in lista_classes:
            nome_classe = classe[2] 

            if nome_classe not in self.tabela_classes:
                continue
            
            #pegando os features
            lista_features = classe[4][1]
            for feature in lista_features:
                linha_feature = feature[1]

                #caso seja funcao
                if feature[0] == "FUNÇÃO":
                    nome_metodo = feature[2]
                    lista_parametros = feature[3][1]
                    tipo_retorno_metodo = feature[4][1]
                    corpo = feature[5][1] 

                    #abro escopo novo para função poder criar suas variaveis somente aqui
                    self.entrar_escopo()

                    for parametro in lista_parametros:

                        if parametro[1] == "self":
                            self.reportar_erro(f"[ERRO SEMANTICO] (Linha {feature[1]}) Parâmetro 'self' inválido no método '{nome_metodo}'.")
                        #adiciono parametro no escopo da sua função, pois podemos usar elas na funcao
                        self.adicionar_variavel(parametro[1], parametro[2][1])
                    
                    #verificando qual vai ser o tipo gerado pelo corpo da função 
                    tipo_inferido = self.checar_expressao(corpo, nome_classe)
                    #verifico se o tipo_inferido é valido para o tipo de retorno
                    if not self.conforma(tipo_inferido, tipo_retorno_metodo):
                        self.reportar_erro(f"[ERRO SEMANTICO] (Linha {linha_feature}) Método '{nome_metodo}': Retorno '{tipo_inferido}' incompatível com '{tipo_retorno_metodo}'.")
                    
                    #função acabou, fecho o escopo e variaveis do escopo morrem
                    self.sair_escopo()


                elif feature[0] == "ATRIBUTO" and len(feature) == 5:
                    nome_attr = feature[2]
                    tipo_declarado = feature[3][1]
                    expr_inicial = feature[4][1]
                    
                    #PEGANDO TIPO DA EXPRESSÃO QUE QUERO ARMAZENAR NO ATRIBUTIO
                    tipo_inferido = self.checar_expressao(expr_inicial, nome_classe)
                    
                    #VERIFICANDO SE CONFORMA
                    if not self.conforma(tipo_inferido, tipo_declarado):
                        self.reportar_erro(f"[ERRO SEMANTICO] (Linha {linha_feature}) Atributo '{nome_attr}': Inicialização '{tipo_inferido}' incompatível com '{tipo_declarado}'.")


    #vai verificar expressoes e retornar os tipos possiveis
    def checar_expressao(self, expr, nome_classe_atual):
        if not isinstance(expr, tuple): 
            return "Object"
        tipo_no = expr[0]

        #Verificando se os tipos dos nós são iguais os tipos bases, então é só retornarr. isso acontecem quando chegamos nas folhas
        if tipo_no == "INTEIRO": 
            return "Int"
        elif tipo_no == "STRING": 
            return "String"
        elif tipo_no == "BOOLEANO": 
            return "Bool"
        
        #variavel, tenho que pegar as infos associadas a ela e buscar a variavel para verificar o tipo dela, e se ela existe
        elif tipo_no == "VARIAVEL":
            linha = expr[1]
            nome_variavel = expr[2]
            #vai buscar variavel na pilha de escopos
            tipo_variavel = self.buscar_variavel(nome_variavel, nome_classe_atual)
            if tipo_variavel is None:
                self.reportar_erro(f"[ERRO SEMANTICO] (Linha {linha}) Variável '{nome_variavel}' não declarada.")
            return tipo_variavel


        #Tratando operações matematicas, a gente verifica o tipo da expressao do lado esquerdo e do lado direito e verificamos se sao iguais a int, se for, podemos retornar um int
        elif tipo_no in ["SOMA", "SUBTRAÇÃO", "MULTIPLICAÇÃO", "DIVISÃO"]:
            linha = expr[1]
            tipo_esq = self.checar_expressao(expr[2], nome_classe_atual)
            tipo_dir = self.checar_expressao(expr[3], nome_classe_atual)
            if tipo_esq != "Int" or tipo_dir != "Int":
                self.reportar_erro(f"[ERRO SEMANTICO] (Linha {linha}) Operação '{tipo_no}' exige inteiros.") 
            return "Int" 
        
        #negação numerica exige que o elemento que vem junto com ela seja um int, se for um int, nos vamos retornar int
        elif tipo_no == "NEGAÇÃO NUMÉRICA":
            linha = expr[1]
            if self.checar_expressao(expr[2], nome_classe_atual) != "Int":
                self.reportar_erro(f"[ERRO SEMANTICO] (Linha {linha}) Operador '~' exige inteiro.")          
            return "Int"
      
        # não logico precisa estar associado a um bool para funcionar, e vai retornar um bool tambem
        elif tipo_no == "NÃO LÓGICO":
            linha = expr[1]
            if self.checar_expressao(expr[2], nome_classe_atual) != "Bool":
                self.reportar_erro(f"[ERRO SEMANTICO] (Linha {linha}) Operador 'not' exige booleano.")
            return "Bool"

        #retorna um bool, ele só avalia se uma variavel é nula
        elif tipo_no == "ISVOID":
            self.checar_expressao(expr[2], nome_classe_atual) 
            return "Bool"

        #menor que e igual que funcionam da mesma forma, precisam ter dois ints e retornam bool
        elif tipo_no in ["MENOR QUE", "MENOR OU IGUAL"]:
            linha = expr[1]
            tipo_esq = self.checar_expressao(expr[2], nome_classe_atual)
            tipo_dir = self.checar_expressao(expr[3], nome_classe_atual)
            if tipo_esq != "Int" or tipo_dir != "Int":
                self.reportar_erro(f"[ERRO SEMANTICO] (Linha {linha}) Comparação exige dois inteiros.")
            return "Bool"

        #igual em cool tem uma peculiaridade, não podemos comparar tipos primarios diferentes, gera erro. tirando isso, segue a mesma logica dos outros de comparar os dois lados e retornar bool
        elif tipo_no == "IGUAL":
            linha = expr[1]
            tipo_esq = self.checar_expressao(expr[2], nome_classe_atual)
            tipo_dir = self.checar_expressao(expr[3], nome_classe_atual)
            basicos = ["Int", "String", "Bool"]
            if (tipo_esq in basicos or tipo_dir in basicos) and (tipo_esq != tipo_dir):
                self.reportar_erro(f"[ERRO SEMANTICO] (Linha {linha}) Tipos básicos incompatíveis na igualdade.")
            return "Bool"
        
        # tratando atribuiçao
        elif tipo_no == "ATRIBUIÇÃO":
            linha = expr[1]
            nome_var = expr[2] 
            expr_valor = expr[3]
            #nome da variavel não pode ser self
            if nome_var == "self":
                self.reportar_erro(f"[ERRO SEMANTICO] (Linha {linha}) Atribuição a 'self' inválida.")

            #descobrindo tipo da variavel olhando o escopo
            tipo_esperado = self.buscar_variavel(nome_var, nome_classe_atual)
            # se não existir tipo, variavel nao foi declarada
            if tipo_esperado is None:
                self.reportar_erro(f"[ERRO SEMANTICO] (Linha {linha}) Variável '{nome_var}' não declarada.")
            #verificando o tipo do que eu quero colocar na variavel
            tipo_real = self.checar_expressao(expr_valor, nome_classe_atual)
            #verificando se os tipos se conformam
            if not self.conforma(tipo_real, tipo_esperado):
                self.reportar_erro(f"[ERRO SEMANTICO] (Linha {linha}) Atribuição incompatível na variável '{nome_var}'.")
            #retorno o tipo do que foi armazenado
            return tipo_real

        #uma regra do cool é o fato de que o tipo de um bloco vai ser sempre igual ao tipo da ultima instrução
        elif tipo_no == "BLOCO":
            tipo_final = "Object"
            #percorro o corpo do bloco analisando o tipo das expressões e no final teremos o tipo da ultima expressao
            for exp in expr[2]:
                tipo_final = self.checar_expressao(exp, nome_classe_atual)
            return tipo_final

        #while retorna sempre object
        elif tipo_no == "WHILE":
            linha = expr[1]
            #while exige que a sua condição seja um bool
            if self.checar_expressao(expr[2][1], nome_classe_atual) != "Bool":
                self.reportar_erro(f"[ERRO SEMANTICO] (Linha {linha}) Condição do 'while' deve ser Bool.")
            # chamo a função de novo só para verificar se o corpo do while nao tem erro, mas não preciso armazenar o tipo, pois while sempre retorna object
            self.checar_expressao(expr[3][1], nome_classe_atual) 
            return "Object"

        #if vai retornar o tipo comum mais proximo entre o corpo do then e else
        elif tipo_no == "IF":
            linha = expr[1]
            #condição do if precisa ser bool
            if self.checar_expressao(expr[2][1], nome_classe_atual) != "Bool":
                self.reportar_erro(f"[ERRO SEMANTICO] (Linha {linha}) Condição do 'if' deve ser Bool.")
            #calculamos os tipos do then e do else
            tipo_then = self.checar_expressao(expr[3][1], nome_classe_atual)
            tipo_else = self.checar_expressao(expr[4][1], nome_classe_atual)
            #retornamos o tipo comum mais proximo entre o then e o else
            return self.juncao_tipos(tipo_then, tipo_else)

        elif tipo_no == "LET":
            #abrindo escopo do let para ele criar suas variaveis
            self.entrar_escopo()
            linha_let = expr[1]
            #pegando as infos das declaracoes
            for decl in expr[2][1]:
                linha_decl = decl[1]
                nome_var = decl[2][1]
                tipo_decl = decl[3][1]
                #variavel nao pode ser self
                if nome_var == "self":
                    self.reportar_erro(f"[ERRO SEMANTICO] (Linha {linha_decl}) 'self' inválido no let.")

                #verificando se os tipos que estou usando existem
                if tipo_decl not in self.tabela_classes and tipo_decl != "SELF_TYPE":
                    self.reportar_erro(f"[ERRO SEMANTICO] (Linha {linha_decl}) Tipo '{tipo_decl}' inexistente no let.")
                
                #se tamanho é 5, estao variavel foi inicializada, entao temos que fazer todo o processo de descobrir o tipo que estamos armazenando na variavel, se elas se conformam e só depois adicionar no escopo
                if len(decl) == 5:
                    tipo_real = self.checar_expressao(decl[4][1], nome_classe_atual)
                    if not self.conforma(tipo_real, tipo_decl):
                        self.reportar_erro(f"[ERRO SEMANTICO] (Linha {linha_decl}) Inicialização let incompatível.")
                self.adicionar_variavel(nome_var, tipo_decl)

            #avaliando o corpo de let
            tipo_corpo = self.checar_expressao(expr[3][1], nome_classe_atual)
            #fechando o escopo e destruindo as variaveis
            self.sair_escopo()
            return tipo_corpo
        
        # criando variavel nova
        elif tipo_no == "NEW":
            linha = expr[1]
            tipo_novo = expr[2] 
            #só verifico se a o nome da classe que estou tentando instanciar existe
            if tipo_novo not in self.tabela_classes and tipo_novo != "SELF_TYPE":
                self.reportar_erro(f"[ERRO SEMANTICO] (Linha {linha}) Instanciação de tipo desconhecido '{tipo_novo}'.")
            #se existir, eu retorno o tipo que tento instanciar
            return tipo_novo

        elif tipo_no == "CASE":
            #avaliando a expressao do case para ver se nao tem nenhum erro
            linha_case = expr[1]
            self.checar_expressao(expr[2][1], nome_classe_atual) 
            # esses vetores são para armazenar quais tipos já foram usados/vistos no case, o cool não permite ter duas linhas de case com mesmo tipo
            tipos_retorno = []
            tipos_vistos = [] 
            
            for ramo in expr[3][1]:
                linha_ramo = ramo[1]
                tipo_ramo = ramo[3][1]
                #verificando justamente se dois ramos possuem mesmo tipo
                if tipo_ramo in tipos_vistos:
                    self.reportar_erro(f"[ERRO SEMANTICO] (Linha {linha_ramo}) Tipo '{tipo_ramo}' duplicado em ramos do case.")
                else:
                    tipos_vistos.append(tipo_ramo)
                
                #entro no escopo do case
                self.entrar_escopo()
                #adiciono a variavel criada
                self.adicionar_variavel(ramo[2][1], tipo_ramo)
                #verifico se não tem erro, e adiciono o tipo na lista de possiveis tipos de retorno
                tipos_retorno.append(self.checar_expressao(ramo[4][1], nome_classe_atual))
                #fecho escopo
                self.sair_escopo()
                
            #aqui a gente vai decidir o tipo de retorno, tentando achar o parente mais proximo entre todos os ramos
            tipo_final = tipos_retorno[0]
            if len(tipos_retorno) > 1:
                for t in tipos_retorno[1:]:
                    tipo_final = self.juncao_tipos(tipo_final, t)
            return tipo_final

        #tratando chamada de metodo, função
        elif tipo_no in ["CHAMADA DE FUNÇÃO", "CHAMADA DE MÉTODO", "CHAMADA ESTÁTICA"]:
            linha = expr[1]
            
            if tipo_no == "CHAMADA DE FUNÇÃO":
                tipo_obj = nome_classe_atual
                nome_metodo = expr[2][1]
                args_ast = expr[3][1]
            else:
                #se não for a chamada de uuma funçaõ, quer dizer que é um metodo ou uma chamada estatica e existe um objeto associado para chamar esses dois, vamos descobrir o tipo desse objeto
                tipo_obj = self.checar_expressao(expr[2][1], nome_classe_atual)

                #se o tipo do obj for self_type quer dizer que ele é do mesmo tipo da sua classe
                if tipo_obj == "SELF_TYPE": 
                    tipo_obj = nome_classe_atual 
                
                # se for chamda de metodo temos que armazenar o nome e seus argumentos
                if tipo_no == "CHAMADA DE MÉTODO":
                    nome_metodo = expr[3][1]
                    args_ast = expr[4][1]

                #se nao for é chamada estatica
                else: 
                    #pegamos o tipo da classe mae
                    tipo_estatico = expr[3][1]
                    #fazemos um teste para ver se o tipo do objeto se conforma com o tipo da mae
                    if not self.conforma(tipo_obj, tipo_estatico):
                        self.reportar_erro(f"[ERRO SEMANTICO] (Linha {linha}) Objeto '{tipo_obj}' incompatível com tipo estático '{tipo_estatico}'.")
                    #tipo do obejto passa a ser o tipo da mae
                    tipo_obj = tipo_estatico 
                    nome_metodo = expr[4][1]
                    args_ast = expr[5][1]

            #verificando se a classe existe
            descritor_classe = self.tabela_classes.get(tipo_obj)
            if not descritor_classe:
                self.reportar_erro(f"[ERRO SEMANTICO] (Linha {linha}) Chamada em tipo desconhecido '{tipo_obj}'.")
                
            #verificando se metodo existe
            metodo_desc = descritor_classe.metodos.get(nome_metodo)
            if not metodo_desc:
                self.reportar_erro(f"[ERRO SEMANTICO] (Linha {linha}) Método '{nome_metodo}' não encontrado em '{tipo_obj}'.")

            #verificando a se o tamanho dos argumentos passados esta correto
            if len(args_ast) != len(metodo_desc.tipo_parametro):
                self.reportar_erro(f"[ERRO SEMANTICO] (Linha {linha}) Argumentos incorretos para '{nome_metodo}'.")
            else:
                #verificando se os tipos dos argumentos passado estao de acrodo
                for i in range(len(args_ast)):
                    tipo_arg_passado = self.checar_expressao(args_ast[i], nome_classe_atual)
                    tipo_esperado = metodo_desc.tipo_parametro[i]
                    if not self.conforma(tipo_arg_passado, tipo_esperado):
                        self.reportar_erro(f"[ERRO SEMANTICO] (Linha {linha}) Argumento incompatível na chamada '{nome_metodo}'.")

            #para nao retornar a palavra self_type, ele retorna o tipo da classe
            if metodo_desc.tipo_retorno == "SELF_TYPE": 
                return tipo_obj
            return metodo_desc.tipo_retorno
       
       #se alguma regra nao bater retorna object
        return "Object"
        

#  EXECUÇÃO PRINCIPAL 
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso correto: python semantico.py <arquivo.cl>")
        sys.exit(1)

    nome_arquivo = sys.argv[1]
    if not nome_arquivo.endswith('.cl'):
        print(f"ERRO: O arquivo '{nome_arquivo}' não é do tipo .cl")
        sys.exit(1)

    try:
        with open(nome_arquivo, 'r', encoding='utf-8') as arquivo:
            codigo_cool = arquivo.read()
    except FileNotFoundError:
        print(f"[ERRO] Arquivo '{nome_arquivo}' não encontrado.")
        sys.exit(1)
        
    print(f"Compilando: {nome_arquivo}...\n")
    arvore_sintatica = parser.parse(codigo_cool, lexer=lexer.clone())
    
    if arvore_sintatica:
        analisador = AnalisadorSemantico(arvore_sintatica)
        analisador.analisar()
        print("\n[SUCESSO] Análise semântica concluída sem erros.")