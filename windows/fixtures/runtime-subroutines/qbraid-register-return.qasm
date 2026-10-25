OPENQASM 3.0;
    include "stdgates.inc";

    def my_function(qubit[4] q) -> bool{
        h q;
        return true;
    }
    qubit[4] q;
    
    // this is to be explained
    bool b = my_function(q);
    