from __future__ import unicode_literals
import logging
from django.template import Library

from ..classes import Link, Menu, SourceColumn
from ..forms import MultiItemForm

register = Library()

logger = logging.getLogger(__name__)

@register.simple_tag()
def get_link(name):
    return Link.get(name)

@register.filter
def get_source_column_metadata(source):
    columns = get_source_columns(source)
    for c in columns:
        if c.label =='Metadata':
            return [c]
    return [] 
    
@register.filter
def get_source_column_thumbnail(source):
    columns = get_source_columns(source)
    for c in columns:
        if c.label =='Thumbnail':
            return [c]
    return [] 

@register.filter
def get_source_column_permissions(source):
    columns = get_source_columns(source)
    for c in columns:
        if c.label =='Permission':
            return [c]
    return [] 

@register.simple_tag()
def get_menu(name):
    return Menu.get(name)


@register.simple_tag(takes_context=True)
def get_menu_links(context, name, source=None, sort_results=None):
    return Menu.get(name).resolve(context=context, source=source, sort_results=sort_results)


@register.simple_tag(takes_context=True)
def get_menus_links(context, names, source=None, sort_results=None):
    result = []

    for name in names.split(','):
        for links in Menu.get(name=name).resolve(context=context, sort_results=sort_results):
            if links:
                result.append(links)

    return result


@register.simple_tag(takes_context=True)
def get_multi_item_links_form(context, object_list):
    actions = []
    for link_set in Menu.get('multi item menu').resolve(context=context, source=object_list[0], sort_results=True):
        for link in link_set:
            actions.append((link.url, link.text))

    form = MultiItemForm(actions=actions)
    context.update({'multi_item_form': form, 'multi_item_actions': actions})
    return ''


@register.filter
def get_source_columns(source):
    try:
        # Is it a query set?
        source = source.model
    except AttributeError:
        # Is not a query set
        try:
            # Is iterable?
            source = source[0]
        except TypeError:
            # It is not an iterable
            pass
        except IndexError:
            # It a list and it's empty
            pass
        except KeyError:
            # It a list and it's empty
            pass

    return SourceColumn.get_for_source(source)


@register.simple_tag(takes_context=True)
def resolve_link(context, link):
    # This can be used to resolve links or menus too
    return link.resolve(context=context)


@register.simple_tag(takes_context=True)
def source_column_resolve(context, column):
    context['column_result'] = column.resolve(context=context)
    return ''
