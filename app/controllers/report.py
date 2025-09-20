# app/controllers/report.py
from app.controllers.aktivitas import list_activities
from app.utils.export_pdf import export_df_to_pdf

def export_report_excel(path, filters=None):
    df = list_activities(filters)
    df.to_excel(path, index=False)

def export_report_pdf(path, filters=None, title="Activity Report"):
    df = list_activities(filters)
    export_df_to_pdf(df, path, title)
