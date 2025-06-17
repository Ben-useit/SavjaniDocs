from __future__ import unicode_literals
from django import forms
from django.utils.html import format_html_join
from django.utils.safestring import mark_safe
from django.contrib.auth import get_user_model
from django.utils import timezone
from common.utils import get_str_from_aware


import logging
logger = logging.getLogger(__name__)
  
def get_metadata_string(document):
    """
    Return a formated representation of a document's metadata values
    """
    html_string = ""
    file_no = document.register.all()
    quotation_no = document.quotation_set.all()
    if file_no:
        html_string += '<span class="metadata-name">File Number:</span><br /><span class="metadata-value"><b>'+file_no[0].file_no.encode("utf-8")+'</b></span><br />'
    if quotation_no:
           html_string += '<span class="metadata-name">Quotation Number:</span><br /><span class="metadata-value"><b>'+unicode(quotation_no[0].file_no)+'</b> - '+unicode(quotation_no[0].parties)+'</span><br />'
 
    for document_metadata in document.metadata.all():
        if str(document_metadata.metadata_type.name) == 'email_date':
            html_string += '<span class="metadata-name">'+ str(document_metadata.metadata_type) +':</span><br /><span class="metadata-value">'+get_str_from_aware(document_metadata.value)+'</span><br />'
        else:           
            html_string += '<span class="metadata-name">'+ str(document_metadata.metadata_type) +':</span><br /><span class="metadata-value">'+unicode(document_metadata.value)+'</span><br />'
        
    return mark_safe(html_string)    


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

class DateTimeWidget(forms.widgets.TextInput):
    date_time = None
    
    def render(self, name, value, attrs=None):
        
        value = get_str_from_aware(str(timezone.now()))
        final_attrs = self.build_attrs(self.attrs, attrs)
        output = '''
        <div class="metadata-value input-group date form_datetime"  data-date-format="" data-link-field="dtp_input1">
        '''
        output += super(DateTimeWidget, self).render(name, value, final_attrs)
        output += '''    <span class="input-group-addon"><span class="glyphicon glyphicon-th" 
            onclick="$(event.target).parents('tr').find('.metadata-update').prop('checked', true);"></span></span>
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
