-- Teste 5: Fatorial recursivo
-- Esperado: fat(5) = 120
class Main {
    fat(n: Int): Int {
        if n <= 1 then
            1
        else
            n * fat(n - 1)
        fi
    };

    main(): Int {
        fat(5)
    };
};
