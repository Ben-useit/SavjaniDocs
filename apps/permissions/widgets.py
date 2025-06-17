from __future__ import absolute_import, unicode_literals

from django import forms
from django.apps import apps
from django.template.loader import render_to_string
from django.utils.encoding import force_text
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .permissions import permission_role_view

import logging
logger = logging.getLogger(__name__)

class RoleFormWidget(forms.SelectMultiple):
    def __init__(self, *args, **kwargs):
        self.queryset = kwargs.pop('queryset')
        return super(RoleFormWidget, self).__init__(*args, **kwargs)

    def render_option(self, selected_choices, option_value, option_label):
        if option_value is None:
            option_value = ''
        option_value = force_text(option_value)
        if option_value in selected_choices:
            selected_html = mark_safe(' selected="selected"')
            if not self.allow_multiple_selected:
                # Only allow for a single selection.
                selected_choices.remove(option_value)
        else:
            selected_html = ''
        return format_html(
            '<option value="{}"{}>{}</option>',
            option_value,
            selected_html,
            force_text(option_label)
        )


from django.forms import widgets

class RoleSelectWidget(widgets.RadioSelect):
    
    def render(self, name, value, attrs=None):
        final_attrs = self.build_attrs(self.attrs, attrs)
        super(RoleSelectWidget, self).render(name, value, final_attrs)
        role_id = final_attrs.get('role_id' or '0')
        name = final_attrs.get('name' or 'Hans')
        members = final_attrs.get('members' or None)
        extra = """
             <table class="table table-sm" style="margin-bottom:0;width:160px;">
               <th style="background-color: #aaa;color:white;">
                  <label class="form-check-label" for="sel1" style="padding-left: 5px;">"""+name+"""</label>                   
                 </th>
                <tr style="background-color: #E74C3C;height:22px;">
                    <td style="line-height:0px;padding-top:3px;padding-left:12px;">

                    <div class="radio-inline">
                    <label><input value='0' title="No access" style="margin-top:0px;" type="radio" name="role_selection-"""+str(role_id)+""""    checked ></label>
                   </div>
                      
                    <div class="radio-inline">
                      <label><input value='1' title="Limited access" style="margin-top:0px;" type="radio" name="role_selection-"""+str(role_id)+"""" ></label>
                    </div>
          
                    <div class="radio-inline">
                      <label><input value='2' title="Full access" style="margin-top:0px;" type="radio" name="role_selection-"""+str(role_id)+"""" ></label>
                    </div>
                    </td>
                </tr>"""
        if members:
            for m in members:
                extra += '<tr style="background-color: #fff3e0;"><td style="padding-left: 13px;">'+m+'</td></tr>'
        else:
            extra += '<tr style="background-color: #fff3e0;"><td style="padding-left: 13px;heigth:30px;"> </td></tr>'
           
        extra += '</table>'

        return extra
