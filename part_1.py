from fpdf import FPDF
from fpdf.enums import XPos, YPos
# https://www.youtube.com/watch?v=q70xzDG6nls&list=PLjNQtX45f0dR9K2sMJ5ad9wVjqslNBIC0
# create FPDF object
# Layout ('P', 'L')
# Unit ('mm', 'cm', 'in')
# format ('A3', 'A4' (default), 'A5', 'Letter', 'Legal', (100,150))
pdf = FPDF('P','mm','Letter')
# add a page
pdf.add_page()
# specify font
# fonts ('times', 'courier', 'helvetica', 'symbol', 'zpfdingbats')
# 'B' (bold), 'U' (underline), 'I' (italics), '' (regular), combination (i.e., ('BU'))
pdf.set_font('helvetica','', 16)

# Add text
# w = width
# h = height
# cell(width, height, content)
#ln=true means go to next line
pdf.cell(40,10, 'Hello World', new_x=XPos.RIGHT,border=True)
pdf.cell(80,10, "Good Bye World", new_x=XPos.LEFT, new_y=YPos.NEXT,border=True)
pdf.cell(80,10, "Good Bye World", new_x=XPos.LEFT, new_y=YPos.NEXT,border=True)
pdf.cell(80,10, "Good Bye World", new_x=XPos.LEFT, new_y=YPos.NEXT,border=True)
pdf.cell(80,10, "Good Bye World", new_x=XPos.LEFT, new_y=YPos.NEXT,border=True)
pdf.cell(80,10, "Good Bye World", new_x=XPos.LEFT, new_y=YPos.NEXT,border=True)
pdf.cell(80,10, "Good Bye World", new_x=XPos.LEFT, new_y=YPos.NEXT,border=True)
pdf.cell(80,10, "Good Bye World", new_x=XPos.LEFT, new_y=YPos.NEXT,border=True)
pdf.cell(80,10, "Good Bye World", new_x=XPos.LEFT, new_y=YPos.NEXT,border=True)
pdf.cell(80,10, "Good Bye World", new_x=XPos.LEFT, new_y=YPos.NEXT,border=True)
pdf.cell(80,10, "Good Bye World", new_x=XPos.LEFT, new_y=YPos.NEXT,border=True)
pdf.cell(80,10, "Good Bye World", new_x=XPos.LEFT, new_y=YPos.NEXT,border=True)
pdf.cell(80,10, "Good Bye World", new_x=XPos.LEFT, new_y=YPos.NEXT,border=True)
pdf.cell(80,10, "Good Bye World", new_x=XPos.LEFT, new_y=YPos.NEXT,border=True)
pdf.cell(80,10, "Good Bye World", new_x=XPos.LEFT, new_y=YPos.NEXT,border=True)
pdf.cell(80,10, "Good Bye World", new_x=XPos.LEFT, new_y=YPos.NEXT,border=True)
pdf.cell(80,10, "Good Bye World", new_x=XPos.LEFT, new_y=YPos.NEXT,border=True)
pdf.cell(80,10, "Good Bye World", new_x=XPos.LEFT, new_y=YPos.NEXT,border=True)
pdf.cell(80,10, "Good Bye World", new_x=XPos.LEFT, new_y=YPos.NEXT,border=True)
pdf.cell(80,10, "Good Bye World", new_x=XPos.LEFT, new_y=YPos.NEXT,border=True)
pdf.cell(80,10, "Good Bye World", new_x=XPos.LEFT, new_y=YPos.NEXT,border=True)
pdf.cell(80,10, "Good Bye World", new_x=XPos.LEFT, new_y=YPos.NEXT,border=True)
pdf.cell(80,10, "Good Bye World", new_x=XPos.LEFT, new_y=YPos.NEXT,border=True)
pdf.cell(80,10, "Good Bye World", new_x=XPos.LEFT, new_y=YPos.NEXT,border=True)
pdf.cell(80,10, "Good Bye World", new_x=XPos.LEFT, new_y=YPos.NEXT,border=True)
pdf.cell(80,10, "Good Bye World", new_x=XPos.LEFT, new_y=YPos.NEXT,border=True)
pdf.cell(80,10, "Good Bye World", new_x=XPos.LEFT, new_y=YPos.NEXT,border=True)
pdf.cell(80,10, "Good Bye World", new_x=XPos.LEFT, new_y=YPos.NEXT,border=True)
pdf.cell(80,10, "Good Bye World", new_x=XPos.LEFT, new_y=YPos.NEXT,border=True)
pdf.cell(80,10, "Good Bye World", new_x=XPos.LEFT, new_y=YPos.NEXT,border=True)
pdf.cell(80,10, "Good Bye World", new_x=XPos.LEFT, new_y=YPos.NEXT,border=True)
pdf.output('pdf_1.pdf')

