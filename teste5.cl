class Main inherits IO {
    main() : Object {
        -- chama calcular antes de ele aparecer no arquivo
        let resultado : Int <- calcular(10) in
            out_int(resultado)
    };

    -- calcular aparece DEPOIS do main no arquivo
    calcular(x : Int) : Int {
        x * 2
    };
};