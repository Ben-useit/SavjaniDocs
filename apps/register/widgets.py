from __future__ import absolute_import, unicode_literals

from django import forms
from django.apps import apps
from django.template.loader import render_to_string
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from django.forms.widgets import NumberInput

class RangeInput(NumberInput):
    input_type = "range"

class UserSelectionWidget(forms.SelectMultiple):

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        result = super(UserSelectionWidget, self).create_option(
            attrs=attrs, index=index,
            label='{}'.format(conditional_escape(label)), name=name,
            selected=selected, subindex=subindex, value=value
        )
        if label.count('|') > 0:
            result['attrs']['data-color'] = '#FFF888'
        else:
            result['attrs']['data-color'] = '#AAF888'
        return result

class DateTimePickerInput(forms.DateTimeInput):
    template_name = 'register/datetimepicker.html'
class DatePickerInput(forms.DateTimeInput):
    template_name = 'register/datepicker.html'

class DateSelectionWidgetDEL(forms.widgets.TextInput):
    last_modified = None

    def render(self, name, value, attrs=None):
        final_attrs = self.build_attrs(self.attrs, attrs)
        output = '''
        <div class="form-group">
        <div class="input-group date form_datetime col-md-5" data-date-format="MM dd yyyy" data-link-field="dtp_input1">
        '''
        output += super(DateSelectionWidget, self).render(name, value, final_attrs)
        output += '''    <span class="input-group-addon"><span class="glyphicon glyphicon-th"></span></span>
                </div>
            <input type="hidden" id="dtp_input1" value="" /><br/>
            </div>
            <script type="text/javascript">
            $('.form_datetime').datetimepicker({
                //language:  'fr',
                weekStart: 1,
                format: 'd. MM yyyy, hh:ii',
                todayBtn:  1,
                autoclose: 1,
                todayHighlight: 1,
                startView: 2,
                forceParse: 0,
                viewSelect: 'year',
                showMeridian: 0
            });
            </script>
            '''
        return output

class CheckListWidget(object):
    def __init__(self, state, center=False, icon_ok=None, icon_fail=None):
        self.state = state

    def render(self):
        if self.state:
            return mark_safe("<span style='color:green;'><i class='fas fa-check'></i></span>")
        else:
            return mark_safe("<span style='background-color:green;color:grey;'></span>")

# ~ class StatusReportWidget(object):
    # ~ def __init__(self, state, center=False, icon_ok=None, icon_fail=None):
        # ~ self.state = state

    # ~ def render(self):
        # ~ if self.state:
            # ~ return mark_safe("<span class ='btn btn-default btn-xs' style='color:blue;background-color: #fff;'><i class='fas fa-file-pdf' style='color: blue'></i> </span>")
        # ~ else:
            # ~ return mark_safe("")



class StatusWidget(object):
    def __init__(self, state, center=False, icon_ok=None, icon_fail=None):
        self.state = state

    def render(self):
        return mark_safe("<span class='btn btn-xs' style='background-color:"+self.state.background_color+";color:"+self.state.color+";'>"+self.state.name+"</span>")
        if self.state == 'Active':
            return mark_safe("<span class='btn btn-xs' style='background-color:green;color:#FFF;'>Active</span>")
        elif self.state == 'Dormant':
            return mark_safe("<span class='btn btn-xs' style='background-color:#888888'>Dormant</span>")
        elif self.state == 'Not active':
            return mark_safe("<span class='btn btn-xs' style='background-color:#f39c12'>Not active</span>")
        elif self.state == 'Closed':
            return mark_safe("<span class='btn btn-xs' style='background-color:red;color:white'>Closed</span>")
        elif self.state == 'Request to close':
            return mark_safe("<span class='btn btn-xs' style='background-color:grey;color:white'>Request to close</span>")
        elif self.state == 'Transferred to client':
            return mark_safe("<span class='btn btn-xs' style='background-color:blue;color:white'>Transferred to client</span>")
        elif self.state == 'Request to transfer':
            return mark_safe("<span class='btn btn-xs' style='background-color:#02075D;color:white'>Request to transfer</span>")
        else:
            return mark_safe("<span sclass='btn btn-xs'>None</span>")

class LawyerFormWidget(forms.SelectMultiple):
    option_template_name = 'register/forms/widgets/lawyer_select_option.html'

    def __init__(self, *args, **kwargs):
        self.queryset = kwargs.pop('queryset')
        self.selected = kwargs.pop('selected',None)
        return super(LawyerFormWidget, self).__init__(*args, **kwargs)

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        full_name = self.queryset.get(pk=value).get_full_name()
        if self.selected and self.queryset.get(pk=value) in self.selected:
            selected = True
        result = super(LawyerFormWidget, self).create_option(
            name=name, value=value, label='{}'.format(conditional_escape(full_name)),
            selected=selected, index=index, subindex=subindex, attrs=attrs
        )

        #result['attrs']['data-color'] = self.queryset.get(pk=value).color

        return result

class FilterFormWidget(forms.SelectMultiple):
    option_template_name = 'register/forms/widgets/lawyer_select_option.html'

    def __init__(self, *args, **kwargs):
        self.queryset = kwargs.pop('queryset')
        self.selected = kwargs.pop('selected',[])
        return super(FilterFormWidget, self).__init__(*args, **kwargs)

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        if self.queryset.get(pk=value) in self.selected:
            selected = True
        result = super(FilterFormWidget, self).create_option(
            name=name, value=value, label='{}'.format(conditional_escape(label)),
            selected=selected, index=index, subindex=subindex, attrs=attrs
        )
        return result
