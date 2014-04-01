'''
Created on Mar 21, 2014

@author: dejans
'''

from django.template import Library

register = Library()

@register.filter
def get_dict_item(dictionary, key):
    return dictionary.get(key, '')

@register.filter
def get_dict_item_stripped_key(dictionary, key):
    print '['  + key + ']'
    return dictionary.get(key.strip(), '')