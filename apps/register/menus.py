from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from navigation import Menu, get_cascade_condition

from .icons import icon_menu_register
from .permissions import permission_register_list

menu_departments = Menu(
    icon_class=icon_menu_register, label=_('Department'), name='department menu'
)
menu_register = Menu(
    condition=get_cascade_condition(
        app_label='register', model_name='Register',
        object_permission=permission_register_list,
        view_permission=permission_register_list,
    ), icon_class=icon_menu_register, label=_('Register'), name='register menu'
)
menu_quotation = Menu(
    condition=get_cascade_condition(
        app_label='register', model_name='Register',
        object_permission=permission_register_list,
        view_permission=permission_register_list,
    ), icon_class=icon_menu_register, label=_('Quotation'), name='quotation menu'
)
