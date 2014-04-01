from __future__ import absolute_import

import re
import types
import logging
import datetime

from django.db.models import Q
from django.db.models.loading import get_model
from django.core.exceptions import PermissionDenied

from acls.models import AccessEntry
from permissions.models import Permission

logger = logging.getLogger(__name__)


class SearchModel(object):
    registry = {}

    @classmethod
    def get_all(cls):
        return cls.registry.values()

    @classmethod
    def get(cls, full_name):
        return cls.registry[full_name]

    def __init__(self, app_label, model_name, label=None, permission=None):
        self.app_label = app_label
        self.model_name = model_name
        self.search_fields = {}
        self.model = get_model(app_label, model_name)
        self.label = label or self.model._meta.verbose_name
        self.permission = permission
        self.__class__.registry[self.get_full_name()] = self

    def get_full_name(self):
        return '%s.%s' % (self.app_label, self.model_name)

    def get_all_search_fields(self):
        return self.search_fields.values()
        
    def get_search_field(self, full_name):
        return self.search_fields[full_name]

    def get_fields_simple_list(self):
        """
        Returns a list of the fields for the SearchModel
        """
        result = []
        for search_field in self.get_all_search_fields():
            result.append((search_field.get_full_name(), search_field.label))

        return result

    def add_model_field(self, *args, **kwargs):
        """
        Add a search field that directly belongs to the parent SearchModel
        """
        search_field = SearchField(self, *args, **kwargs)
        self.search_fields[search_field.get_full_name()] = search_field
    
    def add_related_field(self, *args, **kwargs):
        """
        Add a search field that will search content in a related field in
        a separate model
        """
        search_field = RelatedSearchField(self, *args, **kwargs)
        self.search_fields[search_field.get_full_name()] = search_field

    def normalize_query(self, query_string,
                        findterms=re.compile(r'"([^"]+)"|(\S+)').findall,
                        normspace=re.compile(r'\s{2,}').sub):
        """
        Splits the query string in invidual keywords, getting rid of unecessary spaces
        and grouping quoted words together.
        Example:
            >>> normalize_query('  some random  words "with   quotes  " and   spaces')
            ['some', 'random', 'words', 'with quotes', 'and', 'spaces']
        """
        return [normspace(' ', (t[0] or t[1]).strip()) for t in findterms(query_string)]

    def simple_search(self, query_string, user):
        search_dict = {}

        for search_field in self.get_all_search_fields():
            search_dict.setdefault(search_field.get_model(), {
                'searches': [],
                'label': search_field.label,
                'return_value': search_field.return_value
            })
            search_dict[search_field.get_model()]['searches'].append(
                {
                    'field_name': [search_field.field],
                    'terms': self.normalize_query(query_string)
                }
            )        
        
        logger.debug('search_dict: %s' % search_dict)

        return self.execute_search(search_dict, user, global_and_search=False)

    def advanced_search(self, dictionary, user):
        search_dict = {}
        
        for key, value in dictionary.items():
            logger.debug('key: %s' % key)
            logger.debug('value: %s' % value)

            if key not in ['page'] and value:
                search_field = self.get_search_field(key)
                logger.debug('search_field: %s' % search_field)
                search_dict.setdefault(search_field.get_model(), {
                    'searches': [],
                    'label': search_field.label,
                    'return_value': search_field.return_value
                })
                search_dict[search_field.get_model()]['searches'].append(
                    {
                        'field_name': [search_field.field],
                        'terms': self.normalize_query(value)
                    }
                )  


        logger.debug('search_dict: %s' % search_dict)

        return self.execute_search(search_dict, user, global_and_search=True)

    def execute_search(self, search_dict, user, global_and_search=False):
        start_time = datetime.datetime.now()
        model_list = {}
        list_results = set()

        for model, data in search_dict.items():
            logger.debug('model: %s' % model)

            # Initialize per model result set
            model_result_set = set()

            for query_entry in data['searches']:
                # Fashion a list of queries for a field for each term
                field_query_list = self.assemble_query(query_entry['terms'], query_entry['field_name'])

                logger.debug('field_query_list: %s' % field_query_list)

                # Initialize per field result set
                field_result_set = set()

                # Get results per search field
                for query in field_query_list:
                    logger.debug('query: %s' % query)
                    term_query_result_set = set(model.objects.filter(query).values_list(data['return_value'], flat=True))

                    # Convert the QuerySet to a Python set and perform the
                    # AND operation on the program and not as a query.
                    # This operation ANDs all the field term results
                    # belonging to a single model, making sure to only include
                    # results in the final field result variable if all the terms
                    # are found in a single field.
                    if not field_result_set:
                        field_result_set = term_query_result_set
                    else:
                        field_result_set &= term_query_result_set

                    logger.debug('term_query_result_set: %s' % term_query_result_set)
                    logger.debug('field_result_set: %s' % field_result_set)

                if global_and_search:
                    if not model_result_set:
                        model_result_set = field_result_set
                    else:
                        model_result_set &= field_result_set
                else:
                    model_result_set |= field_result_set

                logger.debug('model_result_set: %s' % model_result_set)

            # Accumulate the field results return values (PK)
            list_results |= model_result_set

        # Return a QuerySet object of search results
        search_results = self.model.objects.filter(pk__in=list_results)
        
        # Filter the search results by the users permissions or ACLS
        if self.permission:
            try:
                Permission.objects.check_permissions(user, [self.permission])
            except PermissionDenied:
                # If user doesn't have global permission, get a list of document
                # for which he/she does hace access use it to filter the
                # provided object_list
                final_object_list = AccessEntry.objects.filter_objects_by_access(self.permission, user, search_results)
            else:
                final_object_list = search_results
        else:
            final_object_list = search_results

        elapsed_time = unicode(datetime.datetime.now() - start_time).split(':')[2]

        return final_object_list, elapsed_time

    def assemble_query(self, terms, search_fields):
        """
        Returns a query, that is a combination of Q objects. That combination
        aims to search keywords within a model by testing the given search fields.
        """
        queries = []
        for term in terms:
            or_query = None
            for field in search_fields:
                q = Q(**{'%s__%s' % (field, 'icontains'): term})
                if or_query is None:
                    or_query = q
                else:
                    or_query = or_query | q

            queries.append(or_query)
        return queries


# SearchField classes
class SearchField(object):
    """
    Search for terms in fields that directly belong to the parent SearchModel
    """
    def __init__(self, search_model, field, label):
        self.search_model = search_model
        self.field = field
        self.label = label
        self.return_value = 'pk'

    def get_full_name(self):
        return self.field

    def get_model(self):
        return self.search_model.model


class RelatedSearchField(object):
    """
    Search for terms in fields that are related to the parent SearchModel
    """
    def __init__(self, search_model, app_label, model_name, field, return_value, label):
        self.search_model = search_model
        self.app_label = app_label
        self.model_name = model_name
        self.field = field
        self.return_value = return_value
        self.model = get_model(app_label, model_name)
        self.label = label

    def get_full_name(self):
        return '%s.%s.%s' % (self.app_label, self.model_name, self.field)

    def get_model(self):
        return self.model
