'''
Created on Mar 19, 2013

@author: dejans
'''
import csv
import logging

logger = logging.getLogger(__name__)

class CSVFile(object):

    def __init__(self, file_object):
        self.file_object = file_object
        
    def get_metadata(self):
        csv_reader = None
        try:
            csv_reader = csv.reader(self.file_object, delimiter='\t')
            metadata_dict = {}
            for rows in csv_reader:
                if len(rows) > 0:
                    file_name = unicode(rows[0], 'utf-8')
                    metadata_dict[file_name] = []
                    counter = 0
                    for row in rows:
                        if counter > 0 and counter % 2 == 1:
                            metadata_dict[file_name].append({rows[counter] : rows[counter+1]})
                        counter += 1
            print metadata_dict
            return metadata_dict
        except csv.Error as ex:
            logger.debug('file %s, line %d: %s' % (self.file_object.name, csv_reader.line_num, ex))
            print 'file %s, line %d: %s' % (self.file_object.name, csv_reader.line_num, ex)
            raise ex
        
def generate_csv_str(metadata_dict):
    csv_str = ''
    for doc, metadata_doc_dict in metadata_dict.items():
        csv_str += doc
        
        for metadata_key, metadata_value in metadata_doc_dict.items():
            csv_str += '\t' + metadata_key  + '\t' + metadata_value 

        csv_str +=  '\n'

    return csv_str
        