import os
import subprocess

class SecIdBimap:
    def __init__(self,type,timestamp=None):
        command="{} ase.util.SecIdBimap -t {}".format(os.environ["JAVA"],type)
        if timestamp is None:
            command+=" --now"
        else:
            command+=" -ts {}".format(timestamp)
        command+=" -f python"
            
        p=subprocess.Popen(command,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE);
        dict=p.stdout.read()
        p.wait()
        
        #print dict
        self._fromSecId=eval(dict);
        
        #invert
        self._toSecId={}
        for k,v in self._fromSecId.iteritems():
            self._toSecId[v]=k
        
    def fromSecId(self,secId):
        return self._fromSecId[secId]
    
    def toSecId(self,id):
        return self._toSecId[id]
    
    def containsSecId(self,secid):
        return secid in self._fromSecId;
    
    def containsXref(self,xref):
        return xref in self._toSecId;

    
    
    