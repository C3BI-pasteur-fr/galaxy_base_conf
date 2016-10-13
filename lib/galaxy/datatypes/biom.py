"""
Created on Mars. 29, 2016

@authors: Mathieu Valade, Institut Pasteur, Paris
@contacts: fabien.mareuil@pasteur.fr
@project: galaxy
@githuborganization: C3BI
biom datatype sniffer
"""

from galaxy.datatypes.text import Json
from metadata import MetadataElement
import json
import os

class Biom( Json ):
    """
        Biom file format description
        http://biom-format.org/
    """
    file_ext = "biom"

    def sniff(self, filename):
        """
        Try to guess the biom filetype.
        It's usually contain 12 keys : id, format, format_url, type,
        generated_by, date, rows, columns, matrix_type,
        matrix_element_type, shape, data.          
        """
        if self._looks_like_json( filename ):
            keys_list = ['rows', 'format', 'type', 'columns',
            'matrix_type', 'generated_by', 'shape', 'format_url',
            'date', 'data', 'id', 'matrix_element_type']
            with open(filename, "r") as fh:
                data = json.load(fh)
                dict_keys = data.keys()
                dict_keys = map(str, dict_keys)
                if keys_list == list(dict_keys):
                    return True
                else:
                    return False
            return False
