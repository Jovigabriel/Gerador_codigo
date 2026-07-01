class Calculadora {
    somar(a: Int, b: Int): Int { a + b };
};

class Main inherits IO {
    calc: Calculadora <- new Calculadora;

    main(): Object {
        {
            -- ERRO 3: Quantidade errada de argumentos (O compilador não deve chegar aqui).
            calc.somar(1, 2);
        }
    };
};