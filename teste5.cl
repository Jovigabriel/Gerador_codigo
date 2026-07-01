class Main inherits IO {
    calcular(x : Int) : Int {
        x * 2
    };
    main() : Object {
        -- chama calcular antes de ele aparecer no arquivo
        let resultado : Int <- calcular(10) in
            out_int(resultado)
    };

    -- calcular aparece DEPOIS do main no arquivo
    
};