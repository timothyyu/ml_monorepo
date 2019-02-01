package ase.data;

public class CalcAttrType extends AttrType {
    ///XXX parhaps create an attr dependency tree here....
    
    public CalcAttrType(String name) {
        super(name, Type.N);
    }
    
    public CalcAttrType(String name, Type datatype) {
        super(name, datatype);
    }
}
