from __future__ import unicode_literals
from datetime import timedelta, date
from fpdf import FPDF, HTMLMixin
import io
from django.http import FileResponse
from django.contrib.auth.models import User
from tempfile import NamedTemporaryFile
from django.contrib.staticfiles.storage import staticfiles_storage


def daterange(date1, date2):
    for n in range(int ((date2 - date1).days)+1):
        yield date1 + timedelta(n)

class TrackingChartPDF(FPDF, HTMLMixin):
    left_margin=15.0
    right_margin=15.0
    bottom_margin = 15.0
    pages_count = 1
    current_x = 20.0


    def __init__(self):
        self.image_path = staticfiles_storage.path("appearance/images/docs96x96.png")
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
        # Furthest position is within the same page, but further down
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
        label = 'EDMS & Co. Active File Tracking Chart Page '
        self.cell(0, 10, label + str(self.page_no()) + '/{nb}', 0, 0, 'R')
        self.set_font('Arial', '',10)


def get_y(data,index):
    y = 0
    for x in range(index):
        y += data[x]
    return y

def print_tracking_chart(tracking_files):

    font = 'Times'
    font_size = 10
    line_height = 6
    text_width = 152
    symbol_width = 6
    months = []
    files = tracking_files.exclude(closure_letter=None).order_by('closure_letter')
    months = []
    if files:
        for dt in daterange(files.first().closure_letter, files.last().closure_letter):
            month = dt.strftime("%B %Y")
            if month not in months:
                months.append(month)

    pdf = TrackingChartPDF()
    pdf.set_left_margin(pdf.left_margin)
    pdf.set_right_margin(pdf.right_margin)
    pdf.set_auto_page_break(True,10)
    pdf.alias_nb_pages()
    pdf.add_page()

    # Title
    pdf.set_y(10.5)
    pdf.set_font('Arial', 'BU',13)
    pdf.multi_cell(0,10,'EDMS & CO.',0,'C')
    pdf.multi_cell(0,10,'CLOSURE OF LITIGATION DEPARTMENTR',0,'C')
    pdf.set_font('Arial', 'B',12)
    pdf.multi_cell(0,6,'ACTIVE FILE TRACKING CHART',0,'C')
    pdf.multi_cell(0,6,', '.join(months),0,'C')

    y = pdf.get_y()
    pdf.set_y(y+5)

    # Start table here
    line_height = 5
    column_width = 32
    column_widths = [25,50,23,23,23,23,35,23,23,23]
    y = pdf.get_y()
    table_top_y = y-1
    max_y = 0

    x = pdf.get_x()

    pdf.set_font('Arial', 'B',font_size)
    header = 'File No'
    pdf.multi_cell(column_widths[0],line_height,header,0,'J')
    if pdf.get_y() > max_y:
        max_y = pdf.get_y()

    pdf.set_y(y)

    pdf.set_x(pdf.left_margin + get_y(column_widths,1))
    header = 'Parties'
    pdf.multi_cell(column_widths[1],line_height,header,0,'J')
    if pdf.get_y() > max_y:
        max_y = pdf.get_y()

    pdf.set_y(y)
    pdf.set_x(pdf.left_margin + get_y(column_widths,2))
    header = 'Date File opened'
    pdf.multi_cell(column_widths[2],line_height,header,0,'L')
    if pdf.get_y() > max_y:
        max_y = pdf.get_y()

    pdf.set_y(y)
    pdf.set_x(pdf.left_margin + get_y(column_widths,3))
    header = 'RETAIN FILE OR TRANSFER REQUIRED'
    pdf.multi_cell(column_widths[3],line_height,header,0,'L')
    if pdf.get_y() > max_y:
        max_y = pdf.get_y()

    pdf.set_y(y)
    pdf.set_x(pdf.left_margin + get_y(column_widths,4))
    header = 'DATE OF CLOSURE LETTER TO CLIENT'
    pdf.multi_cell(column_widths[4],line_height,header,0,'L')
    if pdf.get_y() > max_y:
        max_y = pdf.get_y()

    pdf.set_y(y)
    pdf.set_x(pdf.left_margin + get_y(column_widths,5))
    header = 'INSTRUCTIONS RECEIVED RE FILE TRANSFER'
    pdf.multi_cell(column_widths[5],line_height,header,0,'L')
    if pdf.get_y() > max_y:
        max_y = pdf.get_y()

    pdf.set_y(y)
    pdf.set_x(pdf.left_margin + get_y(column_widths,6))
    header = 'FILE TO NEW LAWYER (NAME) OR CLIENT'
    pdf.multi_cell(column_widths[6],line_height,header,0,'L')
    if pdf.get_y() > max_y:
        max_y = pdf.get_y()

    pdf.set_y(y)
    pdf.set_x(pdf.left_margin + get_y(column_widths,7))
    header = 'NOTICE OF CHANGE OF LEGAL PRACTITIONERS'
    pdf.multi_cell(column_widths[7],line_height,header,0,'J')
    if pdf.get_y() > max_y:
        max_y = pdf.get_y()

    pdf.set_y(y)
    pdf.set_x(pdf.left_margin + get_y(column_widths,8))
    header = 'RECEIPT OF FILE ACKNOWLEDGEMENT'
    pdf.multi_cell(column_widths[8],line_height,header,0,'J')
    if pdf.get_y() > max_y:
        max_y = pdf.get_y()

    pdf.set_y(y)
    pdf.set_x(pdf.left_margin + get_y(column_widths,9))
    header = 'DATE OF COMPLETION OF TRANSFER PROCESS'
    pdf.multi_cell(column_widths[9],line_height,header,0,'J')
    if pdf.get_y() > max_y:
        max_y = pdf.get_y()
    max_y += 1

    pdf.line(pdf.get_x(),table_top_y,pdf.left_margin + get_y(column_widths,10),table_top_y)
    pdf.line(pdf.get_x(),max_y,pdf.left_margin + get_y(column_widths,10),max_y)

    # ~ # Rows
    pdf.set_font('Arial', '',font_size)
    start_pos = pdf.get_vertical_position()
    start_pos[1] = start_pos[1] + 5
    furthest_pos = start_pos #pdf.get_vertical_position()
    current_v_position = 0
    for file in tracking_files:

        pdf.set_vertical_position( start_pos )
        value = str(file.file.file_no)
        pdf.multi_cell(column_widths[0],line_height,value,0,'J')

        furthest_pos = pdf.furthest_vertical_position( pdf.get_vertical_position(), furthest_pos )
        pdf.set_vertical_position( start_pos )
        pdf.current_x = pdf.left_margin + get_y(column_widths,1)
        pdf.set_x(pdf.current_x)
        value = str(file.file.parties)
        pdf.multi_cell(column_widths[1],line_height,value,0,'J')

        furthest_pos = pdf.furthest_vertical_position( pdf.get_vertical_position(), furthest_pos )
        pdf.set_vertical_position( start_pos )
        pdf.current_x = pdf.left_margin + get_y(column_widths,2)
        pdf.set_x(pdf.current_x)
        value = str(file.get_date(file.file.opened))
        pdf.multi_cell(column_widths[2],line_height,value,0,'J')

        furthest_pos = pdf.furthest_vertical_position( pdf.get_vertical_position(), furthest_pos )
        pdf.set_vertical_position( start_pos )
        pdf.current_x = pdf.left_margin + get_y(column_widths,3)
        pdf.set_x(pdf.current_x)
        value = str(file.get_retain_or_transfer_display())
        pdf.multi_cell(column_widths[3],line_height,value,0,'J')

        furthest_pos = pdf.furthest_vertical_position( pdf.get_vertical_position(), furthest_pos )
        pdf.set_vertical_position( start_pos )
        pdf.current_x = pdf.left_margin + get_y(column_widths,4)
        pdf.set_x(pdf.current_x)
        value = str(file.get_date(file.closure_letter))
        pdf.multi_cell(column_widths[4],line_height,value,0,'J')

        furthest_pos = pdf.furthest_vertical_position( pdf.get_vertical_position(), furthest_pos )
        pdf.set_vertical_position( start_pos )
        pdf.current_x = pdf.left_margin + get_y(column_widths,5)
        pdf.set_x(pdf.current_x)
        value = str(file.get_date(file.instructions))
        pdf.multi_cell(column_widths[5],line_height,value,0,'J')

        furthest_pos = pdf.furthest_vertical_position( pdf.get_vertical_position(), furthest_pos )
        pdf.set_vertical_position( start_pos )
        pdf.current_x = pdf.left_margin + get_y(column_widths,6)
        pdf.set_x(pdf.current_x)
        value = str(file.get_client(name=True))
        pdf.multi_cell(column_widths[6],line_height,value,0,'J')

        furthest_pos = pdf.furthest_vertical_position( pdf.get_vertical_position(), furthest_pos )
        pdf.set_vertical_position( start_pos )
        pdf.current_x = pdf.left_margin + get_y(column_widths,7)
        pdf.set_x(pdf.current_x)
        value = str(file.get_date(file.notice))
        pdf.multi_cell(column_widths[7],line_height,value,0,'J')

        furthest_pos = pdf.furthest_vertical_position( pdf.get_vertical_position(), furthest_pos )
        pdf.set_vertical_position( start_pos )
        pdf.current_x = pdf.left_margin + get_y(column_widths,8)
        pdf.set_x(pdf.current_x)
        value = str(file.get_date(file.receipt))
        pdf.multi_cell(column_widths[8],line_height,value,0,'J')

        furthest_pos = pdf.furthest_vertical_position( pdf.get_vertical_position(), furthest_pos )
        pdf.set_vertical_position( start_pos )
        pdf.current_x = pdf.left_margin + get_y(column_widths,9)
        pdf.set_x(pdf.current_x)
        value = str(file.get_date(file.completion))
        pdf.multi_cell(column_widths[9],line_height,value,0,'J')

        furthest_pos = pdf.furthest_vertical_position( pdf.get_vertical_position(), furthest_pos )
        start_pos = furthest_pos
        # add one line
        #pdf.line(pdf.get_x(),start_pos[1],pdf.left_margin + get_y(column_widths,10),start_pos[1])
        #pdf.line(pdf.get_x(),max_y,pdf.left_margin + get_y(column_widths,10),max_y)


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
        pdf.line(pdf.left_margin + get_y(column_widths,9),table_top_y,pdf.left_margin + get_y(column_widths,9),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,10),table_top_y,pdf.left_margin + get_y(column_widths,10),max_y)
        pdf.line(pdf.get_x(),max_y,pdf.left_margin + get_y(column_widths,10),max_y)
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
        pdf.line(pdf.left_margin + get_y(column_widths,9),table_top_y,pdf.left_margin + get_y(column_widths,9),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,10),table_top_y,pdf.left_margin + get_y(column_widths,10),max_y)
        pdf.line(pdf.get_x(),max_y,pdf.left_margin + get_y(column_widths,10),max_y)
        pdf.page=2

        pdf.set_y(furthest_pos[1])
        max_y = pdf.get_y()
        pdf.line(pdf.get_x(),10,pdf.left_margin + get_y(column_widths,10),10)
        pdf.line(pdf.get_x(),10,pdf.get_x(),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,1),10,pdf.left_margin + get_y(column_widths,1),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,2),10,pdf.left_margin + get_y(column_widths,2),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,3),10,pdf.left_margin + get_y(column_widths,3),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,4),10,pdf.left_margin + get_y(column_widths,4),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,5),10,pdf.left_margin + get_y(column_widths,5),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,6),10,pdf.left_margin + get_y(column_widths,6),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,7),10,pdf.left_margin + get_y(column_widths,7),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,8),10,pdf.left_margin + get_y(column_widths,8),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,9),10,pdf.left_margin + get_y(column_widths,9),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,10),10,pdf.left_margin + get_y(column_widths,10),max_y)
        pdf.line(pdf.get_x(),max_y,pdf.left_margin + get_y(column_widths,10),max_y)
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
        pdf.line(pdf.left_margin + get_y(column_widths,9),table_top_y,pdf.left_margin + get_y(column_widths,9),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,10),table_top_y,pdf.left_margin + get_y(column_widths,10),max_y)
        pdf.line(pdf.get_x(),max_y,pdf.left_margin + get_y(column_widths,10),max_y)
        pages = furthest_pos[0]
        for page in range(pages-2):
            pdf.page += 1
            pdf.set_y(-10)
            max_y = pdf.get_y()
            pdf.line(pdf.get_x(),10,pdf.left_margin + get_y(column_widths,10),10)
            pdf.line(pdf.get_x(),10,pdf.get_x(),max_y)
            pdf.line(pdf.left_margin + get_y(column_widths,1),10,pdf.left_margin + get_y(column_widths,1),max_y)
            pdf.line(pdf.left_margin + get_y(column_widths,2),10,pdf.left_margin + get_y(column_widths,2),max_y)
            pdf.line(pdf.left_margin + get_y(column_widths,3),10,pdf.left_margin + get_y(column_widths,3),max_y)
            pdf.line(pdf.left_margin + get_y(column_widths,4),10,pdf.left_margin + get_y(column_widths,4),max_y)
            pdf.line(pdf.left_margin + get_y(column_widths,5),10,pdf.left_margin + get_y(column_widths,5),max_y)
            pdf.line(pdf.left_margin + get_y(column_widths,6),10,pdf.left_margin + get_y(column_widths,6),max_y)
            pdf.line(pdf.left_margin + get_y(column_widths,7),10,pdf.left_margin + get_y(column_widths,7),max_y)
            pdf.line(pdf.left_margin + get_y(column_widths,8),10,pdf.left_margin + get_y(column_widths,8),max_y)
            pdf.line(pdf.left_margin + get_y(column_widths,9),10,pdf.left_margin + get_y(column_widths,9),max_y)
            pdf.line(pdf.left_margin + get_y(column_widths,10),10,pdf.left_margin + get_y(column_widths,10),max_y)
            pdf.line(pdf.get_x(),max_y,pdf.left_margin + get_y(column_widths,10),max_y)
        pdf.page +=1
        pdf.set_y(furthest_pos[1])
        max_y = pdf.get_y()
        pdf.line(pdf.get_x(),10,pdf.left_margin + get_y(column_widths,10),10)
        pdf.line(pdf.get_x(),10,pdf.get_x(),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,1),10,pdf.left_margin + get_y(column_widths,1),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,2),10,pdf.left_margin + get_y(column_widths,2),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,3),10,pdf.left_margin + get_y(column_widths,3),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,4),10,pdf.left_margin + get_y(column_widths,4),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,5),10,pdf.left_margin + get_y(column_widths,5),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,6),10,pdf.left_margin + get_y(column_widths,6),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,7),10,pdf.left_margin + get_y(column_widths,7),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,8),10,pdf.left_margin + get_y(column_widths,8),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,9),10,pdf.left_margin + get_y(column_widths,9),max_y)
        pdf.line(pdf.left_margin + get_y(column_widths,10),10,pdf.left_margin + get_y(column_widths,10),max_y)
        pdf.line(pdf.get_x(),max_y,pdf.left_margin + get_y(column_widths,10),max_y)

    tmp_file = NamedTemporaryFile(delete=False)
    pdf.output(tmp_file.name,'F')
    return tmp_file.name.split('/')[2]









