'''
Created on Apr 1, 2014

@author: dejans
'''
from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()

@register.filter
@stringfilter
def string_trim(value):
    print '['  + value + ']'
    return value.strip()