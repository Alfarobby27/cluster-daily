# app/utils/export_pdf.py
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

def export_df_to_pdf(df, file_path, title="Report"):
    doc = SimpleDocTemplate(file_path, pagesize=A4)
    style = getSampleStyleSheet()
    elems = [Paragraph(title, style['Title']), Spacer(1,12)]
    data = [list(df.columns)]
    for _, row in df.iterrows():
        data.append([str(x) for x in row.tolist()])
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.grey),
        ('GRID',(0,0),(-1,-1),0.25,colors.black),
        ('VALIGN',(0,0),(-1,-1),'TOP'),
    ]))
    elems.append(table)
    doc.build(elems)
