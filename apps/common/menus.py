from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from navigation import Menu

from .icons import icon_menu_about, icon_menu_user

__all__ = (
    'menu_about', 'menu_facet', 'menu_object', 'menu_main', 'menu_multi_item',
    'menu_secondary', 'menu_setup', 'menu_sidebar', 'menu_tools', 'menu_user'
)

menu_about = Menu(
    icon_class=icon_menu_about, label=_(''), name='about menu'
)
menu_facet = Menu(name='object facet')
menu_object = Menu(name='object menu')
menu_main = Menu(name='main menu')
menu_multi_item = Menu(name='multi item menu')
menu_secondary = Menu(name='secondary menu')
menu_setup = Menu(name='setup menu')
menu_sidebar = Menu(name='sidebar menu')
menu_tools = Menu(name='tools menu')
menu_user = Menu(
    icon_class=icon_menu_user, name='user menu', label=_('')
)
