class Calculadora {
    somar(a: Int, b: Int): Int { a + b };
};

class Main inherits IO {
    calc: Calculadora <- new Calculadora;

    main(): Object {
        {
            -- ERRO 1: Método inexistente na classe.
            calc.subtrair(10, 5);

            -- ERRO 2: Argumento com tipo incompatível (O compilador não deve chegar aqui).
            calc.somar(10, "cinco");

            -- ERRO 3: Quantidade errada de argumentos (O compilador não deve chegar aqui).
            calc.somar(1);
        }
    };
};