-- Teste bool 4: bool dentro de if, retornando Int
class Main inherits IO {
    main(): Object {
        let x: Int <- 5 in
            if x < 10 then
                out_int(1)
            else
                out_int(0)
            fi
    };
};
