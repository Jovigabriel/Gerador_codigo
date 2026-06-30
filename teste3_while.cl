-- Teste 3: While com acumulador
-- Esperado: soma 1+2+3+4+5 = 15
class Main {
    main(): Int {
        let soma: Int <- 0,
            i: Int <- 1
        in {
            while i <= 5 loop {
                soma <- soma + i;
                i <- i + 1;
                soma <- soma;
            }
            pool;
            soma;
        }
    };
};
