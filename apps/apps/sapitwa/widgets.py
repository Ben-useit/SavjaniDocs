#from __future__ import absolute_import, unicode_literals

from django import forms
from django.utils.html import conditional_escape

class DateSelectionWidget(forms.widgets.TextInput):

    last_modified = None

    def render(self, name, value, attrs=None, renderer = None):
        final_attrs = self.build_attrs(self.attrs, attrs)
        output = '''
        <div class="input-group date form_datetime" data-date-autoclose=1 data-date-format="MM dd yyyy" data-link-field="dtp_input1">
        '''
        output += super(DateSelectionWidget, self).render(name, value, final_attrs)
        output += '''    <span class="input-group-addon"><span class="glyphicon glyphicon-th"></span></span>
                </div>
            <input type="hidden" id="dtp_input1" value="" />
            <script type="text/javascript">
            $('.form_datetime').datetimepicker({
                //language:  'fr',
                weekStart: 1,
                format: 'd. MM yyyy',
                todayBtn:  1,
                todayHighlight: 1,
                startView: 2,
                forceParse: 0,
                viewSelect: 'year',
                showMeridian: 0
            });
            </script>
            '''
        return output

class DateTimeSelectionWidget(forms.widgets.TextInput):
    last_modified = None

    def render(self, name, value, attrs=None, renderer = None):
        final_attrs = self.build_attrs(self.attrs, attrs)
        output = '''
        <div class="input-group date form_datetime" data-date-format="MM dd yyyy" data-link-field="dtp_input1">
        '''
        output += super(DateTimeSelectionWidget, self).render(name, value, final_attrs)
        output += '''    <span class="input-group-addon"><span class="glyphicon glyphicon-th"></span></span>
                </div>
            <input type="hidden" id="dtp_input1" value="" />
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

class ListTextWidget(forms.TextInput):
    def __init__(self, data_list, name, *args, **kwargs):
        super(ListTextWidget, self).__init__(*args, **kwargs)
        self._name = name
        self._list = data_list
        self.attrs.update({'list':'list__%s' % self._name})

    def render(self, name, value, attrs=None, renderer=None):
        text_html = super(ListTextWidget, self).render(name, value, attrs=attrs)
        data_list = '<datalist id="list__%s">' % self._name
        for item in self._list:
            data_list += '<option value="%s">' % item
        data_list += '</datalist>'

        return (text_html + data_list)

class RegListWidget(forms.TextInput):
    def __init__(self, data_list, name, *args, **kwargs):
        super(RegListWidget, self).__init__(*args, **kwargs)
        self._name = name
        self._list = data_list
        self.attrs.update({'list':'list__%s' % self._name})

    def render(self, name, value, attrs=None, renderer=None):
        text_html = super(RegListWidget, self).render(name, value, attrs=attrs)
        reg_list = '<datalist id="list__%s">' % self._name
        reg_list += self._list
        reg_list += '</datalist>'

        return (text_html + reg_list)



class RoleFormWidget(forms.SelectMultiple):

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        result = super(RoleFormWidget, self).create_option(
            attrs=attrs, index=index,
            label='{}'.format(conditional_escape(label)), name=name,
            selected=selected, subindex=subindex, value=value
        )
        if label.count('|') > 0:
            result['attrs']['data-color'] = '#FFF888'
        else:
            result['attrs']['data-color'] = '#AAF888'
        return result

class TagFormWidget(forms.SelectMultiple):
    def __init__(self, *args, **kwargs):
        return super(TagFormWidget, self).__init__(*args, **kwargs)

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        result = super(TagFormWidget, self).create_option(
            attrs=attrs, index=index,
            label='{}'.format(conditional_escape(label)), name=name,
            selected=selected, subindex=subindex, value=value
        )

        result['attrs']['data-color'] = self.choices.queryset.get(pk=value).color

        return result
