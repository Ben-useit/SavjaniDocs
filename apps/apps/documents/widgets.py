from __future__ import unicode_literals

from django import forms
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from .settings import (
    setting_display_width, setting_display_height, setting_preview_width,
    setting_preview_height, setting_thumbnail_width, setting_thumbnail_height
)


class DocumentPageImageWidget(forms.widgets.Widget):
    template_name = 'documents/forms/widgets/document_page_image_interactive.html'

    def __init__(self, attrs=None):
        default_attrs = {
            'rotation': 0,
            'zoom': 100,
            'width': setting_display_width.value,
            'height': setting_display_height.value,
        }
        if attrs:
            default_attrs.update(attrs)
        super(DocumentPageImageWidget, self).__init__(default_attrs)

    def format_value(self, value):
        if value == '' or value is None:
            return None
        return value


class DocumentPagesCarouselWidget(forms.widgets.Widget):
    """
    Display many small representations of a document's pages
    """
    template_name = 'documents/forms/widgets/document_page_carousel.html'

    def __init__(self, attrs=None):
        default_attrs = {
            'height': setting_preview_height.value,
            'width': setting_preview_width.value,
        }

        if attrs:
            default_attrs.update(attrs)

        super(DocumentPagesCarouselWidget, self).__init__(default_attrs)

    def format_value(self, value):
        if value == '' or value is None:
            return None
        return value


class DocumentPageThumbnailWidget(object):
    def render(self, instance):
        return render_to_string(
            template_name='documents/widgets/document_thumbnail.html',
            context={
                # Disable the clickable link if the document is in the trash
                'disable_title_link': instance.is_in_trash,
                'gallery_name': 'document_list',
                'instance': instance,
                'size_preview_width': setting_preview_width.value,
                'size_preview_height': setting_preview_height.value,
                'size_thumbnail_width': setting_thumbnail_width.value,
                'size_thumbnail_height': setting_thumbnail_height.value,
            }
        )

class LastModifiedWidget(forms.widgets.TextInput):
    last_modified = None
    
    def render(self, name, value, attrs=None):
        final_attrs = self.build_attrs(self.attrs, attrs)
        output = '''
        <div class="form-group">
        <div class="input-group date form_datetime col-md-5" data-date-format="MM dd yyyy - hh:ii" data-link-field="dtp_input1">
        '''
        output += super(LastModifiedWidget, self).render(name, value, final_attrs)
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

def document_link(document):
    return mark_safe('<a href="%s">%s</a>' % (
        document.get_absolute_url(), document)
    )


def widget_document_page_number(document):
    return mark_safe(s=_('Pages: %d') % document.pages.count())


def widget_document_version_page_number(document_version):
    return mark_safe(s=_('Pages: %d') % document_version.pages.count())
