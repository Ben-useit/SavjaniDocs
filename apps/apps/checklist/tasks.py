from __future__ import unicode_literals

from fpdf import FPDF, HTMLMixin
import io
from django.http import FileResponse
from django.contrib.auth.models import User
from tempfile import NamedTemporaryFile
from django.contrib.staticfiles.storage import staticfiles_storage

from register.permissions import permission_register_process_request
from mailer.tasks import task_send
from django.apps import apps
from common.settings import setting_project_url

class StatusPDF(FPDF, HTMLMixin):
    left_margin=15.0
    right_margin=15.0
    bottom_margin = 15.0
    pages_count = 1
    current_x = 20.0


    def __init__(self,register):
        self.image_path = staticfiles_storage.path("appearance/images/docs96x96.png")
        self.register = register
        FPDF.__init__(self,'L')

    def accept_page_break(self):
        "Accept automatic page break or not"
        if self.add_page:
            # do we need to add a page or does one exist?
            if self.page == self.pages_count:
                self.pages_count += 1
                return self.auto_page_break
            else:
                self.page +=1
                self.set_y(self.bottom_margin)
                self.set_x(self.current_x)


    def get_vertical_position(self):
      # Include page and Y position of the document
      return [self.page_no(),self.get_y()]

    def set_vertical_position(self, pos ):
      # Set the page and Y position of the document
      self.page = pos[0]
      self.set_y(pos[1])

    def furthest_vertical_position(self, pos1, pos2 = None ):
        if not pos2 :
            pos2 = self.get_vertical_position();

        # Returns the "furthest" vertical position between two points,
        # based on page and Y position
        # Furthest position is located on another page or
        # Furthest position is within the sa    me page, but further down
        if ( pos1[0] > pos2[0] ) or (pos1[0] == pos2[0] and pos1[1] >pos2[1] ):
            return pos1
        else:
            return pos2

    # Page footer
    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-10)
        # Arial italic 8
        self.set_font('Arial', 'I', 8)
        # Page number
        label = 'EDMS & Co. Status Report '+str(self.register.file_no)+' Page '
        self.cell(0, 10, label + str(self.page_no()) + '/{nb}', 0, 0, 'R')
        self.set_font('Arial', '',10)


def get_y(data,index):
    y = 0
    for x in range(index):
        y += data[x]
    return y

def create_status_report(register,data,date):

    font = 'Times'
    font_size = 10
    line_height = 6
    text_width = 152
    symbol_width = 6

    pdf = StatusPDF(register = register)
    pdf.set_left_margin(pdf.left_margin)
    pdf.set_right_margin(pdf.right_margin)
    pdf.set_auto_page_break(True,10)
    pdf.alias_nb_pages()
    pdf.add_page()

    # Title
    pdf.set_y(10.5)
    pdf.set_font('Arial', 'BU',14)
    pdf.multi_cell(0,10,'EDMS & CO.  STATUS REPORT',0,'C')
    pdf.multi_cell(0,10,'CORPORATE/COMMERCIAL MATTER',0,'C')
    pdf.set_font('Arial', 'B',11)
    pdf.multi_cell(0,10,'FILE NUMBER:'+str(register.file_no),0,'C')
    pdf.set_font('Arial', 'B',11)
    pdf.multi_cell(0,6,'CLIENT NAME:',0,'C')
    pdf.multi_cell(0,6,str(data['client']),0,'C')
    y = pdf.get_y()
    pdf.set_y(y+5)
    pdf.set_font('Arial', 'BU',font_size)
    pdf.cell(0,line_height,'Contact Details:',0,1)
    pdf.set_font('Arial', 'B',font_size)
    pdf.cell(0,line_height,'Name of contact person at client: ',0)
    indent = pdf.left_margin + symbol_width+pdf.get_string_width('Name of contact person at client: ')
    pdf.set_x(indent)
    pdf.set_font('Arial', '',font_size)
    pdf.cell(0,line_height,str(data['contact']),0,1)
    pdf.set_font('Arial', 'B',font_size)
    pdf.cell(0,line_height,'E-mail address: ',0)
    pdf.set_x(indent)
    pdf.set_font('Arial', '',font_size)
    pdf.multi_cell(0,line_height,str(data['email']),0,1)
    pdf.set_font('Arial', 'B',font_size)
    pdf.cell(0,line_height,'Telephone Number: ',0)
    pdf.set_x(indent)
    pdf.set_font('Arial', '',font_size)
    pdf.cell(0,line_height,str(data['phone']),0,1)
    y = pdf.get_y()
    pdf.set_y(y+5)

    # Start table here
    line_height = 5
    column_width = 32
    column_widths = [45,40,30,30,30,20,35,36]
    y = pdf.get_y()
    table_top_y = y-1
    max_y = 0

    x = pdf.get_x()

    pdf.set_font('Arial', 'B',font_size)
    header = 'Description of matter, plus, if applicable, list of documents to be drawn/reviewed'
    pdf.multi_cell(column_widths[0],line_height,header,0,'J')
    if pdf.get_y() > max_y:
        max_y = pdf.get_y()

    pdf.set_y(y)

    pdf.set_x(pdf.left_margin + get_y(column_widths,1))
    header = 'Stage reached (if applicable):'
    pdf.multi_cell(column_widths[1],line_height,header,0,'J')
    if pdf.get_y() > max_y:
        max_y = pdf.get_y()

    pdf.set_y(y)
    pdf.set_x(pdf.left_margin + get_y(column_widths,2))
    header = 'Estimated time for completion:'
    pdf.multi_cell(column_widths[2],line_height,header,0,'L')
    if pdf.get_y() > max_y:
        max_y = pdf.get_y()

    pdf.set_y(y)
    pdf.set_x(pdf.left_margin + get_y(column_widths,3))
    header = 'Estimated Fixed/Capped Costs (delete as applicable):'
    pdf.multi_cell(column_widths[3],line_height,header,0,'L')
    if pdf.get_y() > max_y:
        max_y = pdf.get_y()

    pdf.set_y(y)
    pdf.set_x(pdf.left_margin + get_y(column_widths,4))
    header = 'Documents requiring stamping and/or registration:'
    pdf.multi_cell(column_widths[4],line_height,header,0,'L')
    if pdf.get_y() > max_y:
        max_y = pdf.get_y()

    pdf.set_y(y)
    pdf.set_x(pdf.left_margin + get_y(column_widths,5))
    header = 'Consents/certificate required:'
    pdf.multi_cell(column_widths[5],line_height,header,0,'L')
    if pdf.get_y() > max_y:
        max_y = pdf.get_y()

    pdf.set_y(y)
    pdf.set_x(pdf.left_margin + get_y(column_widths,6))
    header = 'Documents to be returned/sent to client:'
    pdf.multi_cell(column_widths[6],line_height,header,0,'L')
    if pdf.get_y() > max_y:
        max_y = pdf.get_y()

    pdf.set_y(y)
    pdf.set_x(pdf.left_margin + get_y(column_widths,7))
    header = 'Remarks'
    pdf.multi_cell(column_widths[7],line_height,header,0,'J')
    if pdf.get_y() > max_y:
        max_y = pdf.get_y()

    max_y += 1

    pdf.line(pdf.get_x(),table_top_y,pdf.left_margin + get_y(column_widths,8),table_top_y)
    pdf.line(pdf.get_x(),max_y,pdf.left_margin + get_y(column_widths,8),max_y)

    # ~ # Rows
    pdf.set_font('Arial', '',font_size)
    pdf.set_y(max_y+1)
    pdf.set_x(pdf.left_margin)

    start_pos = pdf.get_vertical_position()
    furthest_pos = pdf.get_vertical_position()
    value = str(data['description'])
    pdf.multi_cell(column_widths[0],line_height,value,0,'J')

    furthest_pos = pdf.furthest_vertical_position( pdf.get_vertical_position(), furthest_pos )
    pdf.set_vertical_position( start_pos )
    pdf.current_x = pdf.left_margin + get_y(column_widths,1)
    pdf.set_x(pdf.current_x)
    value = str(data['stage_reached'])
    pdf.multi_cell(column_widths[1],line_height,value,0,'J')

    furthest_pos = pdf.furthest_vertical_position( pdf.get_vertical_position(), furthest_pos )
    pdf.set_vertical_position( start_pos )
    pdf.current_x = pdf.left_margin + get_y(column_widths,2)
    pdf.set_x(pdf.current_x)
    value = str(data['time_to_complete'])
    pdf.multi_cell(column_widths[2],line_height,value,0,'J')

    furthest_pos = pdf.furthest_vertical_position( pdf.get_vertical_position(), furthest_pos )
    pdf.set_vertical_position( start_pos )
    pdf.current_x = pdf.left_margin + get_y(column_widths,3)
    pdf.set_x(pdf.current_x)
    value = str(data['costs'])
    pdf.multi_cell(column_widths[3],line_height,value,0,'J')

    furthest_pos = pdf.furthest_vertical_position( pdf.get_vertical_position(), furthest_pos )
    pdf.set_vertical_position( start_pos )
    pdf.current_x = pdf.left_margin + get_y(column_widths,4)
    pdf.set_x(pdf.current_x)
    value = str(data['stamping'])
    pdf.multi_cell(column_widths[4],line_height,value,0,'J')

    furthest_pos = pdf.furthest_vertical_position( pdf.get_vertical_position(), furthest_pos )
    pdf.set_vertical_position( start_pos )
    pdf.current_x = pdf.left_margin + get_y(column_widths,5)
    pdf.set_x(pdf.current_x)
    value = str(data['consent'])
    pdf.multi_cell(column_widths[5],line_height,value,0,'J')

    furthest_pos = pdf.furthest_vertical_position( pdf.get_vertical_position(), furthest_pos )
    pdf.set_vertical_position( start_pos )
    pdf.current_x = pdf.left_margin + get_y(column_widths,6)
    pdf.set_x(pdf.current_x)
    value = str(data['document_return'])
    pdf.multi_cell(column_widths[6],line_height,value,0,'J')

    furthest_pos = pdf.furthest_vertical_position( pdf.get_vertical_position(), furthest_pos )
    pdf.set_vertical_position( start_pos )
    pdf.current_x = pdf.left_margin + get_y(column_widths,7)
    pdf.set_x(pdf.current_x)
    value = str(data['remarks'])
    pdf.multi_cell(column_widths[7],line_height,value,0,'J')
    furthest_pos = pdf.furthest_vertical_position( pdf.get_vertical_position(), furthest_pos )

    '''
    Depending of the table size three different horizontal lines
    '''
    if furthest_pos[0] == 1:
        pdf.set_vertical_position( furthest_pos );
        max_y = pdf.get_y()+1
        pdf.line(pdf.get_x(),table_top_y,pdf.get_x(),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,1),table_top_y,pdf.left_margin + get_y(column_widths,1),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,2),table_top_y,pdf.left_margin + get_y(column_widths,2),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,3),table_top_y,pdf.left_margin + get_y(column_widths,3),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,4),table_top_y,pdf.left_margin + get_y(column_widths,4),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,5),table_top_y,pdf.left_margin + get_y(column_widths,5),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,6),table_top_y,pdf.left_margin + get_y(column_widths,6),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,7),table_top_y,pdf.left_margin + get_y(column_widths,7),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,8),table_top_y,pdf.left_margin + get_y(column_widths,8),max_y)
        pdf.line(pdf.get_x(),max_y,pdf.left_margin + get_y(column_widths,8),max_y)
    elif furthest_pos[0] == 2:
        pdf.page=1
        pdf.set_y(-10)
        max_y = pdf.get_y()
        pdf.line(pdf.get_x(),table_top_y,pdf.get_x(),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,1),table_top_y,pdf.left_margin + get_y(column_widths,1),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,2),table_top_y,pdf.left_margin + get_y(column_widths,2),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,3),table_top_y,pdf.left_margin + get_y(column_widths,3),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,4),table_top_y,pdf.left_margin + get_y(column_widths,4),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,5),table_top_y,pdf.left_margin + get_y(column_widths,5),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,6),table_top_y,pdf.left_margin + get_y(column_widths,6),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,7),table_top_y,pdf.left_margin + get_y(column_widths,7),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,8),table_top_y,pdf.left_margin + get_y(column_widths,8),max_y)
        pdf.line(pdf.get_x(),max_y,pdf.left_margin + get_y(column_widths,8),max_y)
        pdf.page=2

        pdf.set_y(furthest_pos[1])
        max_y = pdf.get_y()
        pdf.line(pdf.get_x(),10,pdf.left_margin + get_y(column_widths,8),10)
        pdf.line(pdf.get_x(),10,pdf.get_x(),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,1),10,pdf.left_margin + get_y(column_widths,1),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,2),10,pdf.left_margin + get_y(column_widths,2),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,3),10,pdf.left_margin + get_y(column_widths,3),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,4),10,pdf.left_margin + get_y(column_widths,4),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,5),10,pdf.left_margin + get_y(column_widths,5),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,6),10,pdf.left_margin + get_y(column_widths,6),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,7),10,pdf.left_margin + get_y(column_widths,7),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,8),10,pdf.left_margin + get_y(column_widths,8),max_y)
        pdf.line(pdf.get_x(),max_y,pdf.left_margin + get_y(column_widths,8),max_y)
    else:
        #pdf.set_vertical_position( furthest_pos );
        pdf.page = 1
        pdf.set_y(-10)
        max_y = pdf.get_y()
        pdf.line(pdf.get_x(),table_top_y,pdf.get_x(),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,1),table_top_y,pdf.left_margin + get_y(column_widths,1),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,2),table_top_y,pdf.left_margin + get_y(column_widths,2),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,3),table_top_y,pdf.left_margin + get_y(column_widths,3),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,4),table_top_y,pdf.left_margin + get_y(column_widths,4),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,5),table_top_y,pdf.left_margin + get_y(column_widths,5),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,6),table_top_y,pdf.left_margin + get_y(column_widths,6),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,7),table_top_y,pdf.left_margin + get_y(column_widths,7),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,8),table_top_y,pdf.left_margin + get_y(column_widths,8),max_y)
        pdf.line(pdf.get_x(),max_y,pdf.left_margin + get_y(column_widths,8),max_y)
        pages = furthest_pos[0]
        for page in range(pages-2):
            pdf.page += 1
            pdf.set_y(-10)
            max_y = pdf.get_y()
            pdf.line(pdf.get_x(),10,pdf.left_margin + get_y(column_widths,8),10)
            pdf.line(pdf.get_x(),10,pdf.get_x(),max_y)
            pdf.line(pdf.left_margin + get_y(column_widths,1),10,pdf.left_margin + get_y(column_widths,1),max_y)
            pdf.line(pdf.left_margin + get_y(column_widths,2),10,pdf.left_margin + get_y(column_widths,2),max_y)
            pdf.line(pdf.left_margin + get_y(column_widths,3),10,pdf.left_margin + get_y(column_widths,3),max_y)
            pdf.line(pdf.left_margin + get_y(column_widths,4),10,pdf.left_margin + get_y(column_widths,4),max_y)
            pdf.line(pdf.left_margin + get_y(column_widths,5),10,pdf.left_margin + get_y(column_widths,5),max_y)
            pdf.line(pdf.left_margin + get_y(column_widths,6),10,pdf.left_margin + get_y(column_widths,6),max_y)
            pdf.line(pdf.left_margin + get_y(column_widths,7),10,pdf.left_margin + get_y(column_widths,7),max_y)
            pdf.line(pdf.left_margin + get_y(column_widths,8),10,pdf.left_margin + get_y(column_widths,8),max_y)
            pdf.line(pdf.get_x(),max_y,pdf.left_margin + get_y(column_widths,8),max_y)
        pdf.page +=1
        pdf.set_y(furthest_pos[1])
        max_y = pdf.get_y()
        pdf.line(pdf.get_x(),10,pdf.left_margin + get_y(column_widths,8),10)
        pdf.line(pdf.get_x(),10,pdf.get_x(),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,1),10,pdf.left_margin + get_y(column_widths,1),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,2),10,pdf.left_margin + get_y(column_widths,2),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,3),10,pdf.left_margin + get_y(column_widths,3),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,4),10,pdf.left_margin + get_y(column_widths,4),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,5),10,pdf.left_margin + get_y(column_widths,5),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,6),10,pdf.left_margin + get_y(column_widths,6),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,7),10,pdf.left_margin + get_y(column_widths,7),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,8),10,pdf.left_margin + get_y(column_widths,8),max_y)
        pdf.line(pdf.get_x(),max_y,pdf.left_margin + get_y(column_widths,8),max_y)

    pdf.set_y(max_y+5)
    line_height = line_height + 4
    pdf.set_font('Arial', 'B',font_size)
    pdf.cell(10,line_height,'Date:',0,0)
    pdf.set_font('Arial', '',font_size)
    pdf.cell(0,line_height,date,0,1)

    pdf.set_font('Arial', 'B',font_size)
    pdf.cell(30,line_height,'Name of Lawyer:',0,0)
    pdf.set_font('Arial', '',font_size)
    pdf.cell(0,line_height,str(register.get_lawyer_full_name()),0,1)

    pdf.set_font('Arial', 'B',font_size)
    pdf.cell(40,line_height,'Signature of Lawyer:',0,0)
    pdf.set_font('Arial', '',font_size)
    pdf.cell(0,line_height,'__________________________________',0,1)

    tmp_file = NamedTemporaryFile(delete=False)
    pdf.output(tmp_file.name,'F')
    return tmp_file.name.split('/')[2]



def create_status_report1(register,data,date):

    font = 'Times'
    font_size = 10
    line_height = 6
    text_width = 152
    symbol_width = 6

    pdf = StatusPDF(title='')
    pdf.add_page()

    # Title
    pdf.set_y(10.5)
    pdf.set_font('Arial', 'BU',14)
    pdf.multi_cell(0,10,'STATUS REPORT',0,'C')
    pdf.multi_cell(0,10,'CORPORATE/COMMERCIAL MATTER',0,'C')
    pdf.set_font('Arial', 'B',11)
    pdf.multi_cell(0,10,'FILE NUMBER:'+str(register.file_no),0,'C')
    pdf.set_font('Arial', 'B',11)
    pdf.multi_cell(0,6,'PARTIES:',0,'C')
    pdf.multi_cell(0,6,register.parties.encode('Windows-1252'),0,'C')
    y = pdf.get_y()
    pdf.set_y(y+5)
    pdf.set_font('Arial', 'BU',font_size)
    pdf.cell(0,line_height,'Contact Details:',0,1)
    pdf.set_font('Arial', 'B',font_size)
    pdf.cell(0,line_height,'Name of contact person at client: ',0)
    indent = pdf.left_margin + symbol_width+pdf.get_string_width('Name of contact person at client: ')
    pdf.set_x(indent)
    pdf.set_font('Arial', '',font_size)
    pdf.cell(0,line_height,str(data['contact']),0,1)
    pdf.set_font('Arial', 'B',font_size)
    pdf.cell(0,line_height,'E-mail address: ',0)
    pdf.set_x(indent)
    pdf.set_font('Arial', '',font_size)
    pdf.cell(0,line_height,str(data['email']),0,1)
    pdf.set_font('Arial', 'B',font_size)
    pdf.cell(0,line_height,'Telephone Number: ',0)
    pdf.set_x(indent)
    pdf.set_font('Arial', '',font_size)
    pdf.cell(0,line_height,str(data['phone']),0,1)
    y = pdf.get_y()
    pdf.set_y(y+5)

    pdf.set_font('Arial', 'B',font_size)
    header = 'Description of matter, plus, if applicable, list of documents to be drawn/reviewed'
    pdf.cell(0,line_height,header,0,1)
    pdf.set_font('Arial', '',font_size)
    value = str(data['description'])
    pdf.multi_cell(0,line_height,value,0)

    y = pdf.get_y()
    pdf.set_y(y+2)
    pdf.set_font('Arial', 'B',font_size)
    header = 'Stage reached (if applicable):'
    pdf.cell(0,line_height,header,0,1)
    pdf.set_font('Arial', '',font_size)
    value = data['stage_reached']
    pdf.multi_cell(0,line_height,value,0)

    y = pdf.get_y()
    pdf.set_y(y+2)
    pdf.set_font('Arial', 'B',font_size)
    header = 'Estimated time for completion:'
    pdf.cell(0,line_height,header,0,1)
    pdf.set_font('Arial', '',font_size)
    value = str(data['time_to_complete'])
    pdf.multi_cell(0,line_height,value,0)

    y = pdf.get_y()
    pdf.set_y(y+2)
    pdf.set_font('Arial', 'B',font_size)
    header = 'Estimated Fixed/Capped Costs (delete as applicable):'
    pdf.cell(0,line_height,header,0,1)
    pdf.set_font('Arial', '',font_size)
    value = str(data['costs'])
    pdf.multi_cell(0,line_height,value,0)

    y = pdf.get_y()
    pdf.set_y(y+2)
    pdf.set_font('Arial', 'B',font_size)
    header = 'Documents requiring stamping and/or registration:'
    pdf.cell(0,line_height,header,0,1)
    pdf.set_font('Arial', '',font_size)
    value = str(data['stamping'])
    pdf.multi_cell(0,line_height,value,0)

    y = pdf.get_y()
    pdf.set_y(y+2)
    pdf.set_font('Arial', 'B',font_size)
    header = 'Consents/certificate required:'
    pdf.cell(0,line_height,header,0,1)
    pdf.set_font('Arial', '',font_size)
    value = str(data['consent'])
    pdf.multi_cell(0,line_height,value,0)

    y = pdf.get_y()
    pdf.set_y(y+2)
    pdf.set_font('Arial', 'B',font_size)
    header = 'Documents to be returned/sent to client:'
    pdf.cell(0,line_height,header,0,1)
    pdf.set_font('Arial', '',font_size)
    value = str(data['document_return'])
    pdf.multi_cell(0,line_height,value,0)

    y = pdf.get_y()
    pdf.set_y(y+2)
    pdf.set_font('Arial', 'B',font_size)
    header = 'Remarks:'
    pdf.cell(0,line_height,header,0,1)
    pdf.set_font('Arial', '',font_size)
    value = str(data['remarks'])
    pdf.multi_cell(0,line_height,value,0)

    y = pdf.get_y()
    pdf.set_y(y+2)
    line_height = line_height + 4
    pdf.set_font('Arial', 'B',font_size)
    pdf.cell(15,line_height,'Date:',0,0)
    pdf.set_font('Arial', '',font_size)
    pdf.cell(0,line_height,date,0,1)

    pdf.set_font('Arial', 'B',font_size)
    pdf.cell(30,line_height,'Name of Lawyer:',0,0)
    pdf.set_font('Arial', '',font_size)
    pdf.cell(0,line_height,str(register.get_lawyer_full_name()),0,1)

    pdf.set_font('Arial', 'B',font_size)
    pdf.cell(40,line_height,'Signature of Lawyer:',0,0)
    pdf.set_font('Arial', '',font_size)
    pdf.cell(0,line_height,'__________________________________',0,1)

    tmp_file = NamedTemporaryFile(delete=False)
    pdf.output(tmp_file.name,'F')
    return tmp_file.name.split('/')[2]

class PDF(FPDF):
    left_margin=30.0
    indent = 5
    row_height = 5

    def __init__(self,title,today):
        self.image_path = staticfiles_storage.path("appearance/images/docs96x96.png")
        self.title = title
        self.today = today
        FPDF.__init__(self)

    def header(self):
        self.set_left_margin(self.left_margin)

def create_report(register,today):
    pdf = PDF(title=register.registerchecklist_set.first().checklist.name, today=today)
    pdf.add_page()
    queryset = register.matter.all().order_by('template_entry__number')
    font = 'Times'
    font_size = 11
    text_width = 152
    symbol_width = 6
    pdf.image(pdf.image_path,w=6.77)
    pdf.set_font('Arial', 'B', 12)
    # Title
    pdf.set_y(10.5)
    pdf.set_x(pdf.left_margin+8)
    pdf.cell(0, 6, 'EDMS Docs', 0, 1 ) #, 'L')
    pdf.set_font('Times', '', font_size)
    pdf.set_x(pdf.left_margin+8)
    pdf.cell(0, 4, pdf.title, 0, 1 )#, 'L')
    y = pdf.get_y()
    x = pdf.get_x()
    pdf.line(x,y+5,200,y+5)
    pdf.set_y(y+10)
    pdf.set_font(font, '', font_size)
    pdf.cell(symbol_width,4,'1.',0,0)
    pdf.set_x(pdf.left_margin + symbol_width)
    pdf.cell(0,4,'File number:',0,0)
    pdf.set_x(pdf.left_margin + symbol_width+pdf.get_string_width('File number: '))
    pdf.set_font(font, 'B', font_size)
    pdf.cell(0,4, register.file_no,0,1)
    pdf.set_font(font, '', font_size)
    pdf.ln(3)

    pdf.cell(symbol_width,4,'2.',0,0)
    pdf.set_x(pdf.left_margin + symbol_width)
    pdf.cell(0,4, 'Parties: ' ,0,0)
    pdf.set_x(pdf.left_margin + symbol_width+pdf.get_string_width('Parties: '))
    pdf.set_font(font, 'B', font_size)
    pdf.multi_cell(0,4,register.parties,0,0)
    pdf.set_font(font, '', font_size)
    pdf.ln(3)

    #default for empty text area
    empty_ta = '.'
    for a in range(200):
        empty_ta += ' .'

    for q in queryset:
        indent = pdf.indent * q.template_entry.indent
        if q.template_entry.indent == 0:
            symbol_width = 6
        elif q.template_entry.indent == 1:
            symbol_width = 9
        else:
            symbol_width = 6
            indent = indent + 4

        pdf.set_x(pdf.left_margin + indent)
        pdf.cell(symbol_width,4,q.template_entry.symbol,0,0)
        label = q.template_entry.label
        label = label.split(' ')
        out = ''
        for l in label:
            if pdf.get_string_width(out)+pdf.get_string_width(l+' ') < text_width:
                out += l+' '
            else:
                pdf.set_x(pdf.left_margin + indent + symbol_width)
                pdf.cell(0,4,out,0,1)
                out = l
        if out:
            pdf.set_x(pdf.left_margin + indent + symbol_width)
            pdf.cell(pdf.get_string_width(out),4,out,0,0)
            #The value comes next to the label if there is enough space

            #Textareas are always in the next line
            if q.template_entry.entry_type == q.template_entry.TEXTAREA:
                pdf.ln(5)
                pdf.set_x(pdf.left_margin + indent + symbol_width)
                if not q.value:
                    pdf.multi_cell(text_width,4,empty_ta,0,0)
                else:
                    pdf.set_font(font, 'B', font_size)
                    pdf.multi_cell(text_width,4,q.value,0,0)
                    pdf.set_font(font, '', font_size)
            else:
                pdf.set_font(font, 'B', font_size)
                if q.template_entry.entry_type == q.template_entry.TEXT or\
                    q.template_entry.entry_type == q.template_entry.DATE:
                    value_width = pdf.get_string_width(q.value)
                else:
                    value_width = 0
                pdf.set_font(font, '', font_size)
                if pdf.get_string_width(out) + value_width < ( text_width - indent - symbol_width):
                    pdf.set_x(pdf.left_margin + indent + symbol_width + pdf.get_string_width(out))
                else:
                    pdf.ln()
                    pdf.set_x(pdf.left_margin + indent + symbol_width)
                if q.template_entry.entry_type == q.template_entry.YESNO:
                    x = pdf.get_x()
                    pdf.set_y(pdf.get_y()-1)
                    pdf.set_x(x)
                    pdf.set_font(font, 'B', font_size)
                    #pdf.set_font('ZapfDingbats','',font_size)
                    if q.value == 'yes':
                        pdf.cell(0, 6, 'Yes', 0, 1) # '4'
                    elif q.value == 'no':
                        pdf.cell(0, 6, 'No', 0, 1) # '6'
                    else:
                        #pdf.set_font(font,'',font_size)
                        pdf.cell(0, 6, '', 0, 1)
                    pdf.set_font(font,'',font_size)
                elif q.template_entry.entry_type == q.template_entry.CHECKBOX:
                    if q.value == 'True':
                        image_path = staticfiles_storage.path("appearance/images/checked.png")
                        pdf.image(image_path,None, None, 4,4)
                    else:
                        image_path = staticfiles_storage.path("appearance/images/unchecked.png")
                        pdf.image(image_path,None, None, 4,4)
                else:
                    pdf.set_font(font, 'B', font_size)
                    pdf.cell(0,4,q.value,0,1)
                    pdf.set_font(font,'',font_size)
        pdf.ln(3)
    pdf.set_y(pdf.get_y()+10)
    pdf.set_x(pdf.left_margin)
    width = pdf.get_string_width('Checked by: ')
    pdf.cell(width,4,'Checked by: ',0,0)

    #pdf.set_x(pdf.left_margin +width)
    pdf.cell(pdf.get_string_width('User: ')+25,4,". . . . . . . . . . . . . .",0,0)
    #pdf.ln(3)
    pdf.cell(pdf.get_string_width('Date: '),4,'Date: ',0,0)
    #pdf.set_x(pdf.left_margin +width)
    pdf.cell(0,4,today,0,1)
    pdf.ln(6)
    pdf.cell(0,4,'Signature: ',0,0)
    pdf.set_x(pdf.left_margin +width)
    pdf.cell(0,4,'. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .',0,1)

    tmp_file = NamedTemporaryFile(delete=False)
    pdf.output(tmp_file.name,'F')
    return tmp_file.name.split('/')[2]


# ~ class PDF(FPDF):
    # ~ column_open_width = 25
    # ~ column_file_no_width = 30
    # ~ column_parties_width = 105
    # ~ column_group_width = 17
    # ~ column_status_width = 17
    # ~ row_header_height = 12
    # ~ row_height = 4
    # ~ row_border = 0
    # ~ row_header_border = 0
    # ~ def __init__(self,title,today):
        # ~ self.image_path = staticfiles_storage.path("appearance/images/docs96x96.png")
        # ~ self.title = title
        # ~ self.today = today
        # ~ FPDF.__init__(self)
    # ~ def header(self):
        # ~ self.image(self.image_path, 10, 8, 6.77)
        # ~ # Times bold 15
        # ~ self.set_font('Times', 'B', 12)
        # ~ # Title
        # ~ self.set_y(8.5)
        # ~ self.set_x(17)
        # ~ self.cell(0, 6, 'EDMS Docs - '+self.title, 0, 1, 'L')
        # ~ self.set_font('Times', '', 11)
        # ~ self.set_x(17)
        # ~ self.cell(30, 4,'', 0,1,'L')
        # ~ self.set_x(17)
        # ~ self.cell(30, 4,'Covered Period:', 0,0,'L')
        # ~ self.cell(0, 4, "Nothing", 0, 1, 'L')
        # ~ self.set_x(17)
        # ~ self.cell(30, 4, 'Created:', 0, 0, 'L')
        # ~ self.cell(0, 4, self.today, 0, 1, 'L')
        # ~ y = self.get_y()
        # ~ x = self.get_x()
        # ~ self.line(x,y+5,200,y+5)
        # ~ # Line break
        # ~ self.ln(10)
    # ~ def footer(self):
        # ~ # Position at 1.5 cm from bottom
        # ~ self.set_y(-15)
        # ~ # Times italic 8
        # ~ self.set_font('Times', '', 9)
        # ~ # Page number
        # ~ self.cell(0, 10, 'Page ' + str(self.page_no()) , 0, 0, 'R')

def create_report1(queryset,title,today):
    pdf = PDF(title=title, today=today)
    pdf.add_page()
    pdf.set_font('Times','',10)
    left_border_x = pdf.get_x()
    for q in queryset:
        pdf.set_x(left_border_x+q.template_entry.indent*10)
        if q.template_entry.entry_type == q.template_entry.TEXTAREA:
            pdf.cell(0, 6, q.template_entry.label, 0, 1)
            pdf.set_x(left_border_x+5+q.template_entry.indent*10)
            if q.value:
                pdf.cell(0, 25, q.value, 0, 1)
            else:
                pdf.cell(150, 15, q.value, 1, 1)
        elif q.template_entry.entry_type == q.template_entry.YESNO:
            width = pdf.get_string_width(q.template_entry.label)
            pdf.cell(width+3, 6, q.template_entry.label, 0, 0)
            #pdf.set_font('ZapfDingbats','',10)
            pdf.set_font(font, 'B', font_size)
            if q.value == 'yes':
                #pdf.cell(0, 6, '4', 0, 1)
                pdf.cell(0, 6, 'Yes', 0, 1)
            elif q.value == 'no':
                #pdf.cell(0, 6, '6', 0, 1)
                pdf.cell(0, 6, 'No', 0, 1)
            else:
                #pdf.set_font('Times','',10)
                pdf.cell(0, 6, '', 0, 1)
            pdf.set_font('Times','',10)
        elif q.template_entry.entry_type == q.template_entry.CHECKBOX:
            width = pdf.get_string_width(q.template_entry.label)
            pdf.cell(width+3, 6, q.template_entry.label, 0, 0)

            if q.value == True:
                image_path = staticfiles_storage.path("appearance/images/tick_checked_32x32.png")
                pdf.image(image_path,None, None, 4,4)
            else:
                image_path = staticfiles_storage.path("appearance/images/tick_unchecked_32x32.png")
                pdf.image(image_path,None, None, 4,4)

        elif q.template_entry.entry_type == q.template_entry.TEXT or \
                q.template_entry.entry_type == q.template_entry.DATE or \
                q.template_entry.entry_type == q.template_entry.LABEL:

            value = q.template_entry.label + ' '+q.value
            pdf.cell(0, 6, value, 0, 1)
        # ~ y = pdf.get_y()
        # ~ pdf.cell(pdf.column_open_width, pdf.row_height, r.opened.strftime('%d. %b %Y'),pdf.row_border)
        # ~ pdf.multi_cell(pdf.column_file_no_width, pdf.row_height, r.file_no.encode('Windows-1252'),pdf.row_border)
        # ~ new_line_file_no = pdf.get_y()
        # ~ pdf.set_y(y)
        # ~ pdf.set_x(left_border_x+pdf.column_open_width+pdf.column_file_no_width)
        # ~ pdf.multi_cell(pdf.column_parties_width, pdf.row_height, r.parties.encode('Windows-1252') , pdf.row_border)
        # ~ new_line = pdf.get_y()
        # ~ pdf.set_y(y)
        # ~ pdf.set_x(left_border_x+pdf.column_open_width+pdf.column_file_no_width+pdf.column_parties_width)
        # ~ if register:
            # ~ pdf.cell(pdf.column_group_width, pdf.row_height, r.group, pdf.row_border)
        # ~ pdf.set_font('Times', 'B', 8)
        # ~ if r.status == 'Active':
            # ~ pdf.set_text_color(2,112,13)
        # ~ elif r.status == 'Closed':
            # ~ pdf.set_text_color(255,0,0)
        # ~ elif r.status == 'Not active':
            # ~ pdf.set_text_color(243,156,18)
        # ~ elif r.status == 'Transferred to client':
            # ~ pdf.set_text_color(0,0,255)
        # ~ else:
            # ~ pdf.set_text_color(0,0,0)
        # ~ pdf.cell(pdf.column_status_width, pdf.row_height, r.status, pdf.row_border)
        # ~ pdf.set_text_color(0,0,0)
        # ~ pdf.set_font('Times', '', 8)
        # ~ if new_line_file_no > new_line:
            # ~ pdf.set_y(new_line_file_no)
        # ~ else:
            # ~ pdf.set_y(new_line)
        # ~ if new_line > 270.0 or new_line_file_no > 270.0:
            # ~ pdf.add_page()
    tmp_file = NamedTemporaryFile(delete=False)
    pdf.output(tmp_file.name,'F')
    return tmp_file.name.split('/')[2]


def send_checklist_delete_request_mail(user,register):
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

    subject = "EDMSDocs: Request to delete a checklist."
    body ="""
    <body lang="en-US" link="#AE132D" vlink="#AE132D" dir="ltr">
    <div style="padding:10px;">
    <p style="font-variant: normal; letter-spacing: normal; font-style: normal; font-weight: normal">
    """
    body += str(username)
    body += """ requests to delete a checklist:</p>"""
    body += """ Please open the checklist with this link and delete it.</font></p>
    <p style="font-variant: normal; letter-spacing: normal; font-style: normal; font-weight: normal">
    <font color="#000000"><font face="Calibri">"""
    body += """ <p><a href=" """
    body+= str(setting_project_url.value)+'/checklist/'+str(register.pk)+'/view/'
    body += """ " style="color:#AE132D;">"""
    body += str(setting_project_url.value)+'/checklist/'+str(register.pk)+'/view/'
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
