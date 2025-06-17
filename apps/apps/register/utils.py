from __future__ import absolute_import, unicode_literals
from django.http import FileResponse


def open_pdf(response,pdf,title):
    pdf = open('/tmp/'+pdf, 'rb')
    response = FileResponse(pdf)
    title = title.replace('_',' ')
    if title.endswith('csv'):
        title = title.replace('csv','.csv')
    else:
        title += '.pdf'
    response['Content-Disposition'] = "attachment; filename=\""+title+"\""
    return response
