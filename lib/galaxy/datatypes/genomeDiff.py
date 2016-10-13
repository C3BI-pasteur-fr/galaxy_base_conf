"""
Created on Mars. 04, 2016

@authors: Mathieu Valade, Fabien Mareuil, Institut Pasteur, Paris
@contacts: fabien.mareuil@pasteur.fr
@project: galaxy
@githuborganization: C3BI
genomeDiff datatype sniffer
"""

from galaxy.datatypes.tabular import Tabular
from metadata import MetadataElement

class GenomeDiff( Tabular ):
    """Tab delimited data Genomdiff file"""
    file_ext = "gd"
    def __init__(self, **kwd):
        """Initialize genomdiff datatype"""
        Tabular.__init__(self, **kwd)

    def init_meta( self, dataset, copy_from=None ):
        Tabular.init_meta( self, dataset, copy_from=copy_from )
   
    def sniff( self, filename ):
        fh = open( filename )
        header = fh.readline().strip()
        header = header.split("\t")  
        try:
            if len(header) != 2:
                return False
            else:
                if not header[0].startswith( '#' ):
                    return False
                else:
                    hdr = header[0].split('=')
                    if len(hdr) != 2:
                        return False
                    else:
                        if hdr[1] != 'GENOME_DIFF':
                            return False
        except:
            return False
        return True
