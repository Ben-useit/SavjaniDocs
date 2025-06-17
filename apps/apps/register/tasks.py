from __future__ import absolute_import, unicode_literals

from common.settings import setting_project_url
from django.contrib.auth.models import User
from django.utils import timezone
from django.apps import apps
from common.utils import get_str_from_aware
from .permissions import permission_register_edit, permission_register_create, permission_register_process_request
from mailer.tasks import task_send
from sapitwa.utils import get_now
import logging
logger = logging.getLogger(__name__)


from fpdf import FPDF


from django.contrib.staticfiles.storage import staticfiles_storage
class QuotationPDF(FPDF):
    column_open_width = 20
    column_file_no_width = 30 #20
    column_parties_width = 120
    column_group_width = 0
    column_doc_width = 10
    column_status_width = 17
    row_header_height = 12
    row_height = 4
    row_border = 0
    row_header_border = 0
    def __init__(self,title,total,period,today):
        self.image_path = staticfiles_storage.path("appearance/images/docs96x96.png")
        self.title = title
        self.period = period
        self.today = today
        self.total = total
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

        if self.period:
            self.cell(30, 4,'Covered Period:', 0,0,'L')
            self.cell(0, 4, self.period, 0, 1, 'L')

        if self.total:
            self.cell(30, 4,'Total:', 0,0,'L')
            self.cell(0, 4, str(self.total), 0, 1, 'L')
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


class PDF(FPDF):
    column_open_width = 20
    column_file_no_width = 20
    column_parties_width = 85
    column_group_width = 45
    column_doc_width = 10
    column_status_width = 17
    row_header_height = 12
    row_height = 4
    row_border = 0
    row_header_border = 0
    def __init__(self,title,total,period,today):
        self.image_path = staticfiles_storage.path("appearance/images/docs96x96.png")
        self.title = title
        self.period = period
        self.today = today
        self.total = total
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

        if self.period:
            self.cell(30, 4,'Covered Period:', 0,0,'L')
            self.cell(0, 4, self.period, 0, 1, 'L')

        if self.total:
            self.cell(30, 4,'Total:', 0,0,'L')
            self.cell(0, 4, str(self.total), 0, 1, 'L')
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

import io
from PIL import ImageColor
from django.http import FileResponse
from tempfile import NamedTemporaryFile

def create_quotation_report(queryset,title,total, period,today,register=False, user=None):
    pdf = QuotationPDF(title=title,total=total, period=period,today=today)
    pdf.add_page()
    pdf.set_font('Arial', 'B', 8)
    pdf.set_auto_page_break(False)
    pdf.cell(pdf.column_open_width, pdf.row_header_height, 'Opened',pdf.row_header_border)
    pdf.cell(pdf.column_file_no_width, pdf.row_header_height, 'File Number',pdf.row_header_border)
    pdf.cell(pdf.column_parties_width, pdf.row_header_height, 'Parties', pdf.row_header_border)
    # ~ if register:
        # ~ pdf.cell(pdf.column_group_width, pdf.row_header_height, 'Client', pdf.row_header_border)
    pdf.cell(pdf.column_doc_width, pdf.row_header_height, 'Docs', pdf.row_header_border)
    pdf.cell(pdf.column_status_width, pdf.row_header_height, 'Status', pdf.row_header_border,1)
    pdf.set_font('Arial','',8)
    left_border_x = pdf.get_x()
    for r in queryset:
        y = pdf.get_y()
        pdf.cell(pdf.column_open_width, pdf.row_height, r.opened.strftime('%d. %b %Y'),pdf.row_border)
        pdf.multi_cell(pdf.column_file_no_width, pdf.row_height, r.file_no.encode('Windows-1252'),pdf.row_border)
        new_line_file_no = pdf.get_y()
        pdf.set_y(y)
        pdf.set_x(left_border_x+pdf.column_open_width+pdf.column_file_no_width)
        pdf.multi_cell(pdf.column_parties_width, pdf.row_height, r.parties.encode('Windows-1252') , pdf.row_border)
        new_line = pdf.get_y()
        pdf.set_y(y)
        pdf.set_x(left_border_x+pdf.column_open_width+pdf.column_file_no_width+pdf.column_parties_width)
        # ~ if register:
            # ~ pdf.cell(pdf.column_group_width, pdf.row_height, r.get_client_name(), pdf.row_border)
        pdf.cell(pdf.column_doc_width, pdf.row_height, str(r.get_document_count(user=user)), pdf.row_border)
        pdf.set_font('Arial', 'B', 8)
        color = ImageColor.getcolor(r.status.background_color, "RGB")
        pdf.set_text_color(color[0],color[1],color[2])
        pdf.cell(pdf.column_status_width, pdf.row_height, r.status.name, pdf.row_border)
        pdf.set_text_color(0,0,0)
        pdf.set_font('Arial', '', 8)
        if new_line_file_no > new_line:
            pdf.set_y(new_line_file_no)
        else:
            pdf.set_y(new_line)
        if new_line > 270.0 or new_line_file_no > 270.0:
            pdf.add_page()
    tmp_file = NamedTemporaryFile(delete=False)
    pdf.output(tmp_file.name,'F')
    return tmp_file.name.split('/')[2]


def create_report(queryset,title,total, period,today,register=False, user=None):
    pdf = PDF(title=title,total=total, period=period,today=today)
    pdf.add_page()
    pdf.set_font('Arial', 'B', 8)
    pdf.set_auto_page_break(False)
    pdf.cell(pdf.column_open_width, pdf.row_header_height, 'Opened',pdf.row_header_border)
    pdf.cell(pdf.column_file_no_width, pdf.row_header_height, 'File Number',pdf.row_header_border)
    pdf.cell(pdf.column_parties_width, pdf.row_header_height, 'Parties', pdf.row_header_border)
    if register:
        pdf.cell(pdf.column_group_width, pdf.row_header_height, 'Client', pdf.row_header_border)
    pdf.cell(pdf.column_doc_width, pdf.row_header_height, 'Docs', pdf.row_header_border)
    pdf.cell(pdf.column_status_width, pdf.row_header_height, 'Status', pdf.row_header_border,1)
    pdf.set_font('Arial','',8)
    left_border_x = pdf.get_x()
    for r in queryset:
        y = pdf.get_y()
        pdf.cell(pdf.column_open_width, pdf.row_height, r.opened.strftime('%d. %b %Y'),pdf.row_border)
        pdf.multi_cell(pdf.column_file_no_width, pdf.row_height, r.file_no.encode('Windows-1252'),pdf.row_border)
        new_line_file_no = pdf.get_y()
        pdf.set_y(y)
        pdf.set_x(left_border_x+pdf.column_open_width+pdf.column_file_no_width)
        pdf.multi_cell(pdf.column_parties_width, pdf.row_height, r.parties.encode('Windows-1252') , pdf.row_border)
        new_line = pdf.get_y()
        pdf.set_y(y)
        pdf.set_x(left_border_x+pdf.column_open_width+pdf.column_file_no_width+pdf.column_parties_width)
        if register:
            pdf.multi_cell(pdf.column_group_width, pdf.row_height, r.get_client_name(), pdf.row_border)
            new_line_1 = pdf.get_y()
            if new_line_1 > new_line:
                new_line = new_line_1
            pdf.set_y(y)
            pdf.set_x(left_border_x+pdf.column_open_width+pdf.column_file_no_width+pdf.column_parties_width+pdf.column_group_width)

        pdf.cell(pdf.column_doc_width, pdf.row_height, str(r.get_document_count(user=user)), pdf.row_border)
        pdf.set_font('Arial', 'B', 8)
        color = ImageColor.getcolor(r.status.background_color, "RGB")
        pdf.set_text_color(color[0],color[1],color[2])
        pdf.cell(pdf.column_status_width, pdf.row_height, r.status.name, pdf.row_border)
        pdf.set_text_color(0,0,0)
        pdf.set_font('Arial', '', 8)
        if new_line_file_no > new_line:
            pdf.set_y(new_line_file_no)
        else:
            pdf.set_y(new_line)
        if new_line > 270.0 or new_line_file_no > 270.0:
            pdf.add_page()
    tmp_file = NamedTemporaryFile(delete=False)
    pdf.output(tmp_file.name,'F')
    return tmp_file.name.split('/')[2]

class ClientListPDF(FPDF):
    column_client_width = 80
    column_total_width = 20
    column_active_width = 20
    column_not_active_width = 20
    column_dormant_width = 20
    column_closed_width = 20
    column_misc_width = 20
    row_header_height = 12
    row_height = 6
    row_border = 0
    row_header_border = 0
    def __init__(self,title):
        self.image_path = staticfiles_storage.path("appearance/images/docs96x96.png")
        self.title = title
        self.today = get_now(True,True) #timezone.now().strftime('%e %B %Y')
        FPDF.__init__(self)
    def header(self):
        self.image(self.image_path, 10, 8, 6.77)
        # Arial bold 15
        self.set_font('Arial', 'B', 10)
        # Title
        self.set_y(8.5)
        self.set_x(17)
        self.cell(0, 6, 'EDMS Docs - '+self.title, 0, 1, 'L')
        self.set_font('Arial', '', 10)
        self.set_x(17)
        self.cell(20, 4, 'Created:', 0, 0, 'L')
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

def create_department_report(data,title,user):
    pdf = ClientListPDF(title=title)
    pdf.add_page()
    pdf.set_font('Arial', 'B', 10)
    pdf.set_auto_page_break(False)
    pdf.cell(pdf.column_client_width, pdf.row_header_height, 'Department',pdf.row_header_border)
    pdf.cell(pdf.column_active_width, pdf.row_header_height, 'Active',pdf.row_header_border)
    pdf.cell(pdf.column_not_active_width, pdf.row_header_height, 'Not active', pdf.row_header_border)
    pdf.cell(pdf.column_dormant_width, pdf.row_header_height, 'Dormant', pdf.row_header_border)
    pdf.cell(pdf.column_total_width, pdf.row_header_height, 'Total', pdf.row_header_border,1)
    pdf.set_font('Arial', '', 10)
    for x in data:
        pdf.cell(pdf.column_client_width, pdf.row_height, str(x.name),pdf.row_border)
        pdf.cell(pdf.column_active_width, pdf.row_height, str(x.get_no_matters(user,'Active')) , pdf.row_border)
        pdf.cell(pdf.column_not_active_width, pdf.row_height, str(x.get_no_matters(user,'Not active')), pdf.row_border)
        pdf.cell(pdf.column_dormant_width, pdf.row_height, str(x.get_no_matters(user,'Dormant')), pdf.row_border)
        pdf.cell(pdf.column_total_width, pdf.row_height, str(x.get_no_matters(user,'AnAD')),pdf.row_border,1)

    tmp_file = NamedTemporaryFile(delete=False)
    pdf.output(tmp_file.name,'F')
    return tmp_file.name.split('/')[2]

def create_client_report(data,title):
    pdf = ClientListPDF(title=title)
    pdf.add_page()
    pdf.set_font('Arial', 'B', 10)
    pdf.set_auto_page_break(False)
    pdf.cell(200, pdf.row_header_height+2, data[2],pdf.row_header_border,1)
    pdf.cell(pdf.column_client_width, pdf.row_header_height, 'Client',pdf.row_header_border)
    pdf.cell(pdf.column_total_width, pdf.row_header_height, 'Total', pdf.row_header_border)
    pdf.cell(pdf.column_active_width, pdf.row_header_height, 'Active',pdf.row_header_border)
    pdf.cell(pdf.column_not_active_width, pdf.row_header_height, 'Not active', pdf.row_header_border)
    pdf.cell(pdf.column_dormant_width, pdf.row_header_height, 'Dormant', pdf.row_header_border)
    pdf.cell(pdf.column_closed_width, pdf.row_header_height, 'Closed', pdf.row_header_border)
    pdf.cell(pdf.column_misc_width, pdf.row_header_height, 'Misc.', pdf.row_header_border,1)

    totals = data[1]
    pdf.cell(pdf.column_client_width, pdf.row_height, '',pdf.row_border)
    pdf.cell(pdf.column_total_width, pdf.row_height, str(totals[1]),pdf.row_border)
    pdf.cell(pdf.column_active_width, pdf.row_height, str(totals[2]) , pdf.row_border)
    pdf.cell(pdf.column_not_active_width, pdf.row_height, str(totals[3]), pdf.row_border)
    pdf.cell(pdf.column_dormant_width, pdf.row_height, str(totals[4]), pdf.row_border)
    pdf.cell(pdf.column_closed_width, pdf.row_height,str(totals[5]), pdf.row_border)
    pdf.cell(pdf.column_closed_width, pdf.row_height,str(totals[6]), pdf.row_border,1)
    pdf.set_font('Arial','',10)
    left_border_x = pdf.get_x()
    clients_list = data[0]
    for client in clients_list:
        y = pdf.get_y()
        pdf.cell(pdf.column_client_width, pdf.row_height, client[0].name,pdf.row_border)
        pdf.cell(pdf.column_total_width, pdf.row_height, str(client[1]),pdf.row_border)
        pdf.cell(pdf.column_active_width, pdf.row_height, str(client[2]) , pdf.row_border)
        pdf.cell(pdf.column_not_active_width, pdf.row_height, str(client[3]), pdf.row_border)
        pdf.cell(pdf.column_dormant_width, pdf.row_height, str(client[4]), pdf.row_border)
        pdf.cell(pdf.column_closed_width, pdf.row_height, str(client[5]), pdf.row_border)
        pdf.cell(pdf.column_misc_width, pdf.row_height, str(client[6]), pdf.row_border,1)


    tmp_file = NamedTemporaryFile(delete=False)
    pdf.output(tmp_file.name,'F')
    return tmp_file.name.split('/')[2]

class StatisticPDF(FPDF):
    column_open_width = 60
    column_file_no_width = 25
    column_parties_width = 25
    column_group_width = 25
    column_status_width = 25
    row_header_height = 12
    row_height = 6
    row_border = 0
    row_header_border = 0
    def __init__(self,title,period,today):
        self.image_path = staticfiles_storage.path("appearance/images/docs96x96.png")
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

def create_statistic_report(queryset,title,period,today):
    pdf = StatisticPDF(title=title,period=period,today=today)
    pdf.add_page()
    pdf.set_font('Arial', 'B', 12)
    pdf.set_auto_page_break(False)
    pdf.cell(pdf.column_open_width, pdf.row_header_height, 'User',pdf.row_header_border)
    pdf.cell(pdf.column_file_no_width, pdf.row_header_height, 'Active',pdf.row_header_border)
    pdf.cell(pdf.column_parties_width, pdf.row_header_height, 'Not active', pdf.row_header_border)
    pdf.cell(pdf.column_parties_width, pdf.row_header_height, 'Dormant', pdf.row_header_border)
    pdf.cell(pdf.column_group_width, pdf.row_header_height, 'Closed', pdf.row_header_border)
    pdf.cell(pdf.column_status_width, pdf.row_header_height, 'Total', pdf.row_header_border,1)
    pdf.set_font('Arial','',12)
    left_border_x = pdf.get_x()
    for r in queryset:
        y = pdf.get_y()
        pdf.cell(pdf.column_open_width, pdf.row_height, str(r[0]),pdf.row_border)
        pdf.cell(pdf.column_file_no_width, pdf.row_height, str(r[1]),pdf.row_border)
        pdf.cell(pdf.column_parties_width, pdf.row_height, str(r[2]) , pdf.row_border)
        pdf.cell(pdf.column_group_width, pdf.row_height, str(r[3]), pdf.row_border)
        pdf.cell(pdf.column_status_width, pdf.row_height, str(r[4]), pdf.row_border)
        pdf.cell(pdf.column_status_width, pdf.row_height, str(r[5]), pdf.row_border,1)
        # ~ if new_line_file_no > new_line:
            # ~ pdf.set_y(new_line_file_no)
        # ~ else:
            # ~ pdf.set_y(new_line)
        # ~ if new_line > 270.0 or new_line_file_no > 270.0:
            # ~ pdf.add_page()
    tmp_file = NamedTemporaryFile(delete=False)
    pdf.output(tmp_file.name,'F')
    return tmp_file.name.split('/')[2]



def send_register_request_mail(user,register):
    #get the one with permission
    users = User.objects.all()
    recipient = None
    for u in users:
        if not u.is_superuser:
            if permission_register_process_request.stored_permission.requester_has_this(u):
                recipient = u
                break
    UserMailer = apps.get_model(
        app_label='mailer', model_name='UserMailer'
    )
    user_mailer = UserMailer.objects.get(default=True)

    #user who wants permission
    if not user.is_superuser:
        username = user.first_name+" "+user.last_name
    else:
        username = "The system administrator"
    reply_to = user.email

    subject = "EDMSDocs: Request for new file number."
    body ="""
    <body lang="en-US" link="#AE132D" vlink="#AE132D" dir="ltr">
    <div style="padding:10px;">
    <p style="font-variant: normal; letter-spacing: normal; font-style: normal; font-weight: normal">
    <font color="#000000"><font face="Calibri">"""
    body += str(username)
    body += """ requests a new file number:</font></font></font></p>
    <p style="font-variant: normal; letter-spacing: normal; font-style: normal; font-weight: normal">
    <font color="#000000"><font face="Calibri">"""
    body += """Date: """+get_str_from_aware(str(register.opened))+"""<br />"""
    body += """Description: """+register.parties+"""<br />"""
    body += """ <p><a href=" """

    body+= str(setting_project_url.value)+"/register/"+str(register.id)+"/edit/"+str(user.id)+"/"
    body += """ " style="color:#AE132D;">"""
    body += "Create file number"
    body += """
    </a></p></font></font></font></p><hr/>
    Have a great day!

        <p><span style="font-variant: normal"><font color="#000000"><font face="Calibri"><span style="letter-spacing: normal"><span style="font-style: normal"><span style="font-weight: normal">*
        Please do not reply to this email. Your response will not be
        received.<br/>
        </span></span></span></font></font></font></span>"""
    if reply_to:
        body +="""
        <span style="font-variant: normal">
        <font color="#000000"><font face="Calibri">
        <span style="letter-spacing: normal"><span style="font-style: normal"><span style="font-weight: normal">
        </span></span></span></font></font></font></span><span style="font-variant: normal">
        <font color="#000000"><font face="Calibri">
        <span style="letter-spacing: normal"><span style="font-style: normal"><span style="font-weight: normal">Contact:
        <a href="mailto:"""
        body += reply_to
        body += """ " style="color:#AE132D;">"""
        body += reply_to
        body += """</a></span></span></span></font></font></font></span></p>"""
    body +="""</div>
    <p><img src="https://docs.EDMSandco.mw/docs96x96.png" name="docs" width=60 height=60 align="middle" border="0"/>

    <font face="Calibri"><b>EDMSDocs</b></font></p></body>
    """
    task_send.apply_async(
        kwargs={
            'as_attachment': False,
            'body': body,
            'document_id': None,
            'recipient': recipient.email,
            'sender': "",
            'subject': subject,
            'user_mailer_id': user_mailer.id,
        }
    )

def send_register_request_close_mail(user,register,id_list):
    #get the one with permission
    users = User.objects.all()
    recipient = None
    for u in users:
        if not u.is_superuser:
            if permission_register_process_request.stored_permission.requester_has_this(u):
                recipient = u
                break
    UserMailer = apps.get_model(
        app_label='mailer', model_name='UserMailer'
    )
    user_mailer = UserMailer.objects.get(default=True)

    #user who wants permission
    if not user.is_superuser:
        username = user.first_name+" "+user.last_name
    else:
        username = "The system administrator"
    reply_to = user.email

    subject = "EDMSDocs: Request to close a file."
    body ="""
    <body lang="en-US" link="#AE132D" vlink="#AE132D" dir="ltr">
    <div style="padding:10px;">
    <p style="font-variant: normal; letter-spacing: normal; font-style: normal; font-weight: normal">
    """
    body += str(username)
    body += """ requests to close a file:</p>"""
    body += """ Please edit the files with status "Request to close"</font></p>
    <p style="font-variant: normal; letter-spacing: normal; font-style: normal; font-weight: normal">
    <font color="#000000"><font face="Calibri">"""
    body += """ <p><a href=" """
    body+= str(setting_project_url.value)+"/register/list/"+id_list.replace(',','_')+'/'
    body += """ " style="color:#AE132D;">"""
    body += """File List"""
    body += """
    </a></p></font></p><hr/>
    Have a great day!

        <p><span style="font-variant: normal"><font color="#000000"><font face="Calibri"><span style="letter-spacing: normal"><span style="font-style: normal"><span style="font-weight: normal">*
        Please do not reply to this email. Your response will not be
        received.<br/>
        </span></span></span></font></font></font></span>"""
    if reply_to:
        body +="""
        <span style="font-variant: normal">
        <font color="#000000"><font face="Calibri">
        <span style="letter-spacing: normal"><span style="font-style: normal"><span style="font-weight: normal">
        </span></span></span></font></font></font></span><span style="font-variant: normal">
        <font color="#000000"><font face="Calibri">
        <span style="letter-spacing: normal"><span style="font-style: normal"><span style="font-weight: normal">Contact:
        <a href="mailto:"""
        body += reply_to
        body += """ " style="color:#AE132D;">"""
        body += reply_to
        body += """</a></span></span></span></font></font></font></span></p>"""
    body +="""</div>
    <p><img src="https://docs.EDMSandco.mw/docs96x96.png" name="docs" width=60 height=60 align="middle" border="0"/>

    <font face="Calibri"><b>EDMSDocs</b></font></p></body>
    """
    task_send.apply_async(
        kwargs={
            'as_attachment': False,
            'body': body,
            'document_id': None,
            'recipient': recipient.email,
            'sender': "",
            'subject': subject,
            'user_mailer_id': user_mailer.id,
        }
    )

def send_register_request_transfer_mail(user,register,id_list):
    #get the one with permission
    users = User.objects.all()
    recipient = None
    for u in users:
        if not u.is_superuser:
            if permission_register_process_request.stored_permission.requester_has_this(u):
                recipient = u
                break
    UserMailer = apps.get_model(
        app_label='mailer', model_name='UserMailer'
    )
    user_mailer = UserMailer.objects.get(default=True)

    #user who wants permission
    if not user.is_superuser:
        username = user.first_name+" "+user.last_name
    else:
        username = "The system administrator"
    reply_to = user.email

    subject = "EDMSDocs: Request to transfer a file."
    body ="""
    <body lang="en-US" link="#AE132D" vlink="#AE132D" dir="ltr">
    <div style="padding:10px;">
    <p style="font-variant: normal; letter-spacing: normal; font-style: normal; font-weight: normal">
    """
    body += str(username)
    body += """ requests to transfer a file:</p>"""
    body += """ Please edit the files with status "Request to transfer"</font></p>
    <p style="font-variant: normal; letter-spacing: normal; font-style: normal; font-weight: normal">
    <font color="#000000"><font face="Calibri">"""
    body += """ <p><a href=" """
    body+= str(setting_project_url.value)+"/register/list/"+id_list.replace(',','_')+'/'
    body += """ " style="color:#AE132D;">"""
    body += """File List"""
    body += """
    </a></p></font></p><hr/>
    Have a great day!

        <p><span style="font-variant: normal"><font color="#000000"><font face="Calibri"><span style="letter-spacing: normal"><span style="font-style: normal"><span style="font-weight: normal">*
        Please do not reply to this email. Your response will not be
        received.<br/>
        </span></span></span></font></font></font></span>"""
    if reply_to:
        body +="""
        <span style="font-variant: normal">
        <font color="#000000"><font face="Calibri">
        <span style="letter-spacing: normal"><span style="font-style: normal"><span style="font-weight: normal">
        </span></span></span></font></font></font></span><span style="font-variant: normal">
        <font color="#000000"><font face="Calibri">
        <span style="letter-spacing: normal"><span style="font-style: normal"><span style="font-weight: normal">Contact:
        <a href="mailto:"""
        body += reply_to
        body += """ " style="color:#AE132D;">"""
        body += reply_to
        body += """</a></span></span></span></font></font></font></span></p>"""
    body +="""</div>
    <p><img src="https://docs.EDMSandco.mw/docs96x96.png" name="docs" width=60 height=60 align="middle" border="0"/>

    <font face="Calibri"><b>EDMSDocs</b></font></p></body>
    """
    task_send.apply_async(
        kwargs={
            'as_attachment': False,
            'body': body,
            'document_id': None,
            'recipient': recipient.email,
            'sender': "",
            'subject': subject,
            'user_mailer_id': user_mailer.id,
        }
    )

def send_register_request_confirmation_mail(sender,recipient_id, register):
    try:
        recipient = User.objects.get(pk=recipient_id)
    except User.DoesNotExist:
        return
    UserMailer = apps.get_model(
        app_label='mailer', model_name='UserMailer'
    )
    user_mailer = UserMailer.objects.get(default=True)

    reply_to = sender.email

    subject = "EDMSDocs: New file number has been created"
    body ="""
    <body lang="en-US" link="#AE132D" vlink="#AE132D" dir="ltr">
    <div style="padding:10px;">
    <p style="font-variant: normal; letter-spacing: normal; font-style: normal; font-weight: normal">
    <font color="#000000"><font face="Calibri">"""
    body += """ A new file number has been created:</font></font></font></p>
    <p style="font-variant: normal; letter-spacing: normal; font-style: normal; font-weight: normal">
    <font color="#000000"><font face="Calibri">"""
    body += """Date: """+get_str_from_aware(str(register.opened))+"""<br />"""
    body += """File No: """+str(register.file_no)+"""<br />"""
    body += """Description: """+register.parties+"""<br />"""
    body += """Status: """+register.status+"""<br />"""
    body += """ <p>Have a great day!</p><hr/>
        <p><span style="font-variant: normal"><font color="#000000"><font face="Calibri"><span style="letter-spacing: normal"><span style="font-style: normal"><span style="font-weight: normal">*
        Please do not reply to this email. Your response will not be
        received.<br/>
        </span></span></span></font></font></font></span>"""
    if reply_to:
        body +="""
        <span style="font-variant: normal">
        <font color="#000000"><font face="Calibri">
        <span style="letter-spacing: normal"><span style="font-style: normal"><span style="font-weight: normal">
        </span></span></span></font></font></font></span><span style="font-variant: normal">
        <font color="#000000"><font face="Calibri">
        <span style="letter-spacing: normal"><span style="font-style: normal"><span style="font-weight: normal">Contact:
        <a href="mailto:"""
        body += reply_to
        body += """ " style="color:#AE132D;">"""
        body += reply_to
        body += """</a></span></span></span></font></font></font></span></p>"""
    body +="""</div>
    <p><img src="https://docs.EDMSandco.mw/docs96x96.png" name="docs" width=60 height=60 align="middle" border="0"/>

    <font face="Calibri"><b>EDMSDocs</b></font></p></body>
    """
    task_send.apply_async(
        kwargs={
            'as_attachment': False,
            'body': body,
            'document_id': None,
            'recipient': recipient.email,
            'sender': "",
            'subject': subject,
            'user_mailer_id': user_mailer.id,
        }
    )

def send_quotation_request_confirmation_mail(sender,recipient_id, register):
    try:
        recipient = User.objects.get(pk=recipient_id)
    except User.DoesNotExist:
        return
    UserMailer = apps.get_model(
        app_label='mailer', model_name='UserMailer'
    )
    user_mailer = UserMailer.objects.get(default=True)
    reply_to = sender.email
    subject = "EDMSDocs: New quotation number has been created"
    body ="""
    <body lang="en-US" link="#AE132D" vlink="#AE132D" dir="ltr">
    <div style="padding:10px;">
    <p style="font-variant: normal; letter-spacing: normal; font-style: normal; font-weight: normal">
    <font color="#000000"><font face="Calibri">"""
    body += """ A new quotation number has been created:</font></font></font></p>
    <p style="font-variant: normal; letter-spacing: normal; font-style: normal; font-weight: normal">
    <font color="#000000"><font face="Calibri">"""
    body += """Date: """+get_str_from_aware(str(register.opened))+"""<br />"""
    body += """Quotation Number: """+str(register.file_no)+"""<br />"""
    body += """Description: """+register.parties+"""<br />"""
    body += """Status: """+register.status+"""<br />"""
    body += """ <p>Have a great day!</p><hr/>
        <p><span style="font-variant: normal"><font color="#000000"><font face="Calibri"><span style="letter-spacing: normal"><span style="font-style: normal"><span style="font-weight: normal">*
        Please do not reply to this email. Your response will not be
        received.<br/>
        </span></span></span></font></font></font></span>"""
    if reply_to:
        body +="""
        <span style="font-variant: normal">
        <font color="#000000"><font face="Calibri">
        <span style="letter-spacing: normal"><span style="font-style: normal"><span style="font-weight: normal">
        </span></span></span></font></font></font></span><span style="font-variant: normal">
        <font color="#000000"><font face="Calibri">
        <span style="letter-spacing: normal"><span style="font-style: normal"><span style="font-weight: normal">Contact:
        <a href="mailto:"""
        body += reply_to
        body += """ " style="color:#AE132D;">"""
        body += reply_to
        body += """</a></span></span></span></font></font></font></span></p>"""
    body +="""</div>
    <p><img src="https://docs.EDMSandco.mw/docs96x96.png" name="docs" width=60 height=60 align="middle" border="0"/>

    <font face="Calibri"><b>EDMSDocs</b></font></p></body>
    """
    task_send.apply_async(
        kwargs={
            'as_attachment': False,
            'body': body,
            'document_id': None,
            'recipient': recipient.email,
            'sender': "",
            'subject': subject,
            'user_mailer_id': user_mailer.id,
        }
    )

def send_quotation_request_mail(user,register):
    #get the one with permission
    users = User.objects.all()
    recipient = None
    for u in users:
        if not u.is_superuser:
            if permission_register_process_request.stored_permission.requester_has_this(u):
                recipient = u
                break
    UserMailer = apps.get_model(
        app_label='mailer', model_name='UserMailer'
    )
    user_mailer = UserMailer.objects.get(default=True)

    #user who wants permission
    if not user.is_superuser:
        username = user.first_name+" "+user.last_name
    else:
        username = "The system administrator"
    reply_to = user.email

    subject = "EDMSDocs: Request for new quotation number."
    body ="""
    <body lang="en-US" link="#AE132D" vlink="#AE132D" dir="ltr">
    <div style="padding:10px;">
    <p style="font-variant: normal; letter-spacing: normal; font-style: normal; font-weight: normal">
    <font color="#000000"><font face="Calibri">"""
    body += str(username)
    body += """ requests a new file number:</font></font></font></p>
    <p style="font-variant: normal; letter-spacing: normal; font-style: normal; font-weight: normal">
    <font color="#000000"><font face="Calibri">"""
    body += """Date: """+get_str_from_aware(str(register.opened))+"""<br />"""
    body += """Description: """+register.parties+"""<br />"""
    body += """ <p><a href=" """
    body+= str(setting_project_url.value)+"/register/"+str(register.id)+"/quotation/"+str(user.id)+"/edit/"
    body += """ " style="color:#AE132D;">"""
    body += "Create quotation number"
    body += """
    </a></p></font></font></font></p><hr/>
    Have a great day!

        <p><span style="font-variant: normal"><font color="#000000"><font face="Calibri"><span style="letter-spacing: normal"><span style="font-style: normal"><span style="font-weight: normal">*
        Please do not reply to this email. Your response will not be
        received.<br/>
        </span></span></span></font></font></font></span>"""
    if reply_to:
        body +="""
        <span style="font-variant: normal">
        <font color="#000000"><font face="Calibri">
        <span style="letter-spacing: normal"><span style="font-style: normal"><span style="font-weight: normal">
        </span></span></span></font></font></font></span><span style="font-variant: normal">
        <font color="#000000"><font face="Calibri">
        <span style="letter-spacing: normal"><span style="font-style: normal"><span style="font-weight: normal">Contact:
        <a href="mailto:"""
        body += reply_to
        body += """ " style="color:#AE132D;">"""
        body += reply_to
        body += """</a></span></span></span></font></font></font></span></p>"""
    body +="""</div>
    <p><img src="https://docs.EDMSandco.mw/docs96x96.png" name="docs" width=60 height=60 align="middle" border="0"/>

    <font face="Calibri"><b>EDMSDocs</b></font></p></body>
    """
    task_send.apply_async(
        kwargs={
            'as_attachment': False,
            'body': body,
            'document_id': None,
            'recipient': recipient.email,
            'sender': "",
            'subject': subject,
            'user_mailer_id': user_mailer.id,
        }
    )
