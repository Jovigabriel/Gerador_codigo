class Filha inherits Mae {
    falar() : String {
        "Sou a filha!"
    };
};

class Mae inherits Object {
    nome : String <- "Mae";

    apresentar() : String {
        "Sou a mae!"
    };
};