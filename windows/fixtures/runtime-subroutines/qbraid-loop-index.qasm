
    OPENQASM 3.0;
    include "stdgates.inc";
    def my_function(qubit qin, int[32] iter) -> int[32]{
        h qin;
        if(iter>2)
            x qin;
        if (iter>3)
            y qin;
        return iter + 1;
    }
    qubit[4] q;
    int[32] new_var ;
    for int i in [0:3]
    { 
        new_var = my_function(q[i] , i);
    }

    if(new_var>2)
        h q[0];
    