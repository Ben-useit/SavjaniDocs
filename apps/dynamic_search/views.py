from __future__ import unicode_literals

import logging
import re
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.views.generic.base import RedirectView

from common.generics import SimpleView, SingleObjectListView

from .forms import SearchForm, AdvancedSearchForm, MySearch
from .icons import icon_search_submit
from .mixins import SearchModelMixin
from .settings import setting_limit
from documents.models import Document
from documents.permissions import permission_document_view
from acls.models import AccessControlList
from django.apps import apps

from django.db.models import Q
from django.shortcuts import render
from django.shortcuts import render_to_response
from metadata.models import DocumentMetadata

from document_parsing.models import DocumentPageContent
from ocr.models import DocumentPageOCRContent

logger = logging.getLogger(__name__)


class ResultsView(SearchModelMixin, SingleObjectListView):

    def get_extra_context(self):
        context = {
            'hide_links': True,
            'list_as_items': True,
            'no_results_icon': icon_search_submit,
            'no_results_text': _(
                'Try again using different terms. '
            ),
            'no_results_title': _('No search results'),
            'search_model': self.search_model,
            'search_results_limit': setting_limit.value,
            'title': _('Search results for: %s') % self.search_model.label,
        }

        return context

    def get_context_data(self, **kwargs):
        context = super(ResultsView, self).get_context_data(**kwargs)
        context.update({'objects_without_permission': self.queryset2 })

        return context
    
    def get_object_list(self):
        self.search_model = self.get_search_model()

        if self.request.GET:
            # Only do search if there is user input, otherwise just render
            # the template with the extra_context

            if self.request.GET.get('_match_all', 'off') == 'on':
                global_and_search = True
            else:
                global_and_search = False

            #if s.o searches content search ocr as well
            query_string = self.request.GET.copy()
            if 'content__content' in self.request.GET:
                query_string['ocr_content__content'] = self.request.GET['content__content']
            if 'versions__pages__content__content' in self.request.GET:
                query_string['versions__pages__ocr_content__content'] = self.request.GET['versions__pages__content__content']
            queryset, timedelta = self.search_model.search(
                query_string=query_string, user=self.request.user,
                global_and_search=global_and_search
            )
            queryset1 = AccessControlList.objects.filter_by_access(
                permission_document_view, user=self.request.user, queryset=queryset
            )
            self.queryset2 = queryset.difference(queryset1)
            return queryset1


class SearchView(SearchModelMixin, SimpleView):
    template_name = 'appearance/generic_form.html'
    title = _('Search')

    def get_extra_context(self):
        self.search_model = self.get_search_model()
        return {
            'form': self.get_form(),
            'form_action': reverse(
                'search:results', args=(self.search_model.get_full_name(),)
            ),
            'search_model': self.search_model,
            'submit_icon_class': icon_search_submit,
            'submit_label': _('Search'),
            'submit_method': 'GET',
            'title': _('Search for: %s') % self.search_model.label,
        }

    def get_form(self):
        if ('q' in self.request.GET) and self.request.GET['q'].strip():
            query_string = self.request.GET['q']
            return SearchForm(initial={'q': query_string})
        else:
            return SearchForm()


class AdvancedSearchView(SearchView):
    title = _('Advanced search')

    def get_form(self):
        return AdvancedSearchForm(
            data=self.request.GET, search_model=self.get_search_model()
        )


class SearchAgainView(RedirectView):
    pattern_name = 'search:search_advanced'
    query_string = True
    
    
#new    

from django.db.models import Q
from documents.models import Document
import shlex
class CustomResultsView(SearchModelMixin, SingleObjectListView):
    metadata_dic = {}
    register_dic = {}
    form = None
    q = None
    
    def get_extra_context(self):
        context = {
            'hide_links': True,
            'list_as_items': True,
            'metadata_dic': self.metadata_dic,
            'form' : self.form, 
            'q': self.q,            
            'no_results_icon': icon_search_submit,
            'no_results_text': _(
                'Try again using different terms. '
            ),
            'no_results_title': _('No search results'),
            'search_model': self.search_model,
            'search_results_limit': setting_limit.value,
            'title': _('Search results for query: %s') % self.request.GET.copy()['q'],
            'title_no_permission': 'Other documents:'
        }

        return context

    def get_context_data(self, **kwargs):
        context = super(CustomResultsView, self).get_context_data(**kwargs)
        context.update({'objects_without_permission': self.queryset2 })

        return context
    
    def get_object_list(self):
        self.search_model = self.get_search_model()

        if self.request.GET:
            # Only do search if there is user input, otherwise just render
            # the template with the extra_context

            # ~ if self.request.GET.get('_match_all', 'off') == 'on':
                # ~ global_and_search = True
            # ~ else:
                # ~ global_and_search = False
            #if s.o searches content search ocr as well
            query_string = self.request.GET.copy()['q']
            queries = shlex.split(query_string)

            q_all = Q() # Create an empty Q object to start with
            for q in queries:
                q_objects = Q()
                q_objects.add(Q(**{'%s__%s' % ('label', 'icontains'): q }), Q.OR)
                q_objects.add(Q(**{'%s__%s' % ('metadata__value', 'icontains'): q }), Q.OR)
                q_objects.add(Q(**{'%s__%s' % ('register__file_no', 'icontains'): q }), Q.OR)
                q_objects.add(Q(**{'%s__%s' % ('register__parties', 'icontains'): q }), Q.OR)
                q_all.add(q_objects,Q.AND)
            queryset =  Document.objects.filter(q_all)

            #are there some filters active?           
            filter_query = {}
            register_query = {}
            register_des_query = {}
            for k, v in self.request.GET.iteritems():
                if 'File No' == k and v != '0':
                    register_query[str(k)] = v
                elif 'Parties' == k and v != '0':
                    register_des_query[str(k)] = v
                elif v != '0' and k != 'page' and v != '' and v != 'None'  and k != 'q' and k != 'csrfmiddlewaretoken' :
                    filter_query[str(k)] = v

            for k,v in filter_query.iteritems():
                queryset = queryset.filter(Q(metadata__metadata_type__label = k, metadata__value=v))
            for k,v in register_query.iteritems():
                queryset = queryset.filter(Q(register__file_no = v))
            for k,v in register_des_query.iteritems():
                queryset = queryset.filter(Q(register__parties = v))
            self.metadata_dic = {}
            self.register_dic = {}
            self.register_dic['File No'] = set()
            self.register_dic['Parties'] = set()
            for doc in queryset:
                metas = doc.metadata.all()
                regs = doc.register.all()
                for meta in metas:
                   
                    if meta.metadata_type in self.metadata_dic:
                        self.metadata_dic[meta.metadata_type].add(meta.value)
                    else:
                        self.metadata_dic[meta.metadata_type] = set()
                        self.metadata_dic[meta.metadata_type].add(meta.value)
                for r in regs:
                    self.register_dic['File No'].add(r.file_no)
                    self.register_dic['Parties'].add(r.parties)

            queryset1 = AccessControlList.objects.filter_by_access(
                permission_document_view, user=self.request.user, queryset=queryset
            ).distinct()
            self.queryset2 = queryset.difference(queryset1)
            self.q = self.request.GET['q']
            self.form = MySearch(self.request.GET,metas = self.metadata_dic, register = self.register_dic)            

            return queryset1

''' splits the query string in invidual keywords '''
def normalize_query(query_string,
                    findterms=re.compile(r'"([^"]+)"|(\S+)').findall,
                    normspace=re.compile(r'\s{2,}').sub):

    return [normspace(' ', (t[0] or t[1]).strip()) for t in findterms(query_string)]

def get_query(query_string, search_fields, or_query = True):

    query = None # Query to search for every search term        
    terms = normalize_query(query_string)
    for term in terms:
        or_query = None # Query to search for a given term in each field
        for field_name in search_fields:
            q = Q(**{"%s__icontains" % field_name: term})
            if or_query is None:
                or_query = q
            else:
                or_query = or_query | q  # or
                
        if query is None:
            query = or_query
        elif or_query:
            query = query | or_query # or 
        else:
            query = query & or_query # and 
            
    return query
        
