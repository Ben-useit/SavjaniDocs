from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from navigation import Menu, get_cascade_condition

from register.icons import icon_menu_register
from register.permissions import permission_register_list

menu_checklist = Menu(
    condition=get_cascade_condition(
        app_label='checklist', model_name='Checklist',
        object_permission=permission_register_list,
        view_permission=permission_register_list,
    ), icon_class=icon_menu_register, label=_('CL'), name='checklist menu'
)
# ~ menu_quotation = Menu(
    # ~ condition=get_cascade_condition(
        # ~ app_label='register', model_name='Register',
        # ~ object_permission=permission_register_list,
        # ~ view_permission=permission_register_list,
    # ~ ), icon_class=icon_menu_register, label=_('Quotation'), name='quotation menu'
# ~ )
