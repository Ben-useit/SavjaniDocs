from __future__ import absolute_import, unicode_literals

from common.settings import setting_project_url
from django.contrib.auth.models import User
from django.utils import timezone
from django.apps import apps
from common.utils import get_str_from_aware
from register.permissions import permission_register_edit, permission_register_create, permission_register_process_request
from mailer.tasks import task_send

import logging
logger = logging.getLogger(__name__)


from fpdf import FPDF


from django.contrib.staticfiles.storage import staticfiles_storage
class PDF(FPDF):
    column_open_width = 25
    column_file_no_width = 30
    column_parties_width = 60
    column_client_width = 45
    column_transfer_width = 106
    column_status_width = 17
    row_header_height = 12
    row_height = 4
    row_border = 0
    row_header_border = 0
    def __init__(self,title,period,today):
        self.image_path = staticfiles_storage.path("appearance/images/docs96x96.png")
        #self.image_path_exchange = staticfiles_storage.path("appearance/images/exchange-alt-solid.png")
        self.title = title
        self.period = period
        self.today = today
        FPDF.__init__(self)
    def header(self):
        self.image(self.image_path, 10, 8, 6.77)
        # Arial bold 15
        self.set_font('Arial', 'B', 12)
        # Title
        self.set_y(8.5)
        self.set_x(17)
        self.cell(0, 6, 'EDMS Docs - '+self.title, 0, 1, 'L')
        self.set_font('Arial', '', 11)
        self.set_x(17)
        self.cell(30, 4,'', 0,1,'L')
        self.set_x(17)
        self.cell(30, 4,'Covered Period:', 0,0,'L')
        self.cell(0, 4, self.period, 0, 1, 'L')
        self.set_x(17)
        self.cell(30, 4, 'Created:', 0, 0, 'L')
        self.cell(0, 4, self.today, 0, 1, 'L')
        y = self.get_y()
        x = self.get_x()
        self.line(x,y+5,200,y+5)
        # Line break
        self.ln(10)
    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        # Arial italic 8
        self.set_font('Arial', '', 9)
        # Page number
        self.cell(0, 10, 'Page ' + str(self.page_no()) , 0, 0, 'R')


def action_get_transferred(action, user):
    if action.description.find(user.get_full_name()) > 20:
        return (True,action.description.split('</b>')[0][20:])
    return (False,action.description.split('</b>')[1][7:])

import io
from django.http import FileResponse
from tempfile import NamedTemporaryFile
def create_report(data_dict,total_dict,title,period,today, user=None):
    pdf = PDF(title=title,period=period,today=today)
    pdf.add_page()
    pdf.set_auto_page_break(False)
    for lawyer,data in data_dict.items():
        pdf.set_font('Arial','B',10)
        pdf.cell(150, pdf.row_height+2, lawyer.get_full_name(), pdf.row_border,1)
        #pdf.set_font('Arial','',8)
        #pdf.cell(150, pdf.row_height, 'Total matters: '+ str(total_dict[lawyer.pk]), pdf.row_border,1)
        pdf.set_font('Arial','B',8)
        pdf.cell(pdf.column_open_width, pdf.row_header_height, 'Opened',pdf.row_header_border)
        pdf.cell(pdf.column_file_no_width, pdf.row_header_height, 'Number',pdf.row_header_border)
        pdf.cell(pdf.column_parties_width, pdf.row_header_height, 'Parties', pdf.row_header_border)
        pdf.cell(pdf.column_client_width, pdf.row_header_height, 'Client', pdf.row_header_border)
        pdf.cell(pdf.column_status_width, pdf.row_header_height, 'Status', pdf.row_header_border,1)
        pdf.set_font('Arial','',8)
        left_border_x = pdf.get_x()
        '''
        data is a list of dictionaries
        [{ register: [ Action, Action, ... ] }, { register .... ]
        '''
        for item in data:
            for register, actions in item.items():
                y = pdf.get_y()
                pdf.cell(pdf.column_open_width, pdf.row_height, register.opened.strftime('%d.%m.%Y'),pdf.row_border)
                pdf.set_font('Arial', 'B', 8)
                pdf.cell(pdf.column_file_no_width, pdf.row_height, register.file_no.encode('Windows-1252'),pdf.row_border)
                pdf.set_font('Arial', '', 8)
                parties = register.parties.encode('Windows-1252')
                w = pdf.get_string_width(parties)
                if w > 47:
                    parties = parties[:38]+' ...'
                pdf.cell(pdf.column_parties_width, pdf.row_height, parties , pdf.row_border)
                clients = register.get_client_name()
                w = pdf.get_string_width(clients)
                if w > 40:
                    clients = clients[:29]+' ...'
                pdf.cell(pdf.column_client_width, pdf.row_height, clients, pdf.row_border)
                pdf.set_text_color(0,0,0)
                pdf.set_font('Arial', '', 8)
                if register.status == 'Active':
                    pdf.set_text_color(2,112,13)
                elif register.status == 'Closed':
                    pdf.set_text_color(255,0,0)
                elif register.status == 'Dormant':
                    pdf.set_text_color(136,136,136)
                elif register.status == 'Not active':
                    pdf.set_text_color(243,156,18)
                elif register.status == 'Transferred to client':
                    pdf.set_text_color(0,0,255)
                else:
                    pdf.set_text_color(0,0,0)
                pdf.cell(pdf.column_status_width, pdf.row_height, register.status, pdf.row_border, 1)
                pdf.set_text_color(0,0,0)
                pdf.set_font('Arial', '', 8)
                for a in actions:
                    pdf.set_x(pdf.column_open_width+left_border_x)
                    pdf.cell(pdf.column_file_no_width, pdf.row_height, a.timestamp.strftime('%d.%m.%Y'), pdf.row_border, )
                    pdf.cell(pdf.column_status_width, pdf.row_height, a.description.replace('<b>','').replace('</b>',''), pdf.row_border, 1)
                    if pdf.get_y() > 270:
                        pdf.add_page()
                pdf.set_y(pdf.get_y()+2)
                if pdf.get_y() > 270:
                    pdf.add_page()

    tmp_file = NamedTemporaryFile(delete=False)
    pdf.output(tmp_file.name,'F')
    return tmp_file.name.split('/')[2]

