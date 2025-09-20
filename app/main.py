# app/main.py
import sys
from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow, QDialog, QFileDialog, QMessageBox, QVBoxLayout
from pathlib import Path
from app.models.db import init_db, get_connection
from app.models.importer import preview_file, import_from_file
from app.models.clustering import run_kmeans_and_save as clustering_run
from app.controllers.auth import authenticate, register_user
from app.controllers.aktivitas import list_activities, insert_activity, update_activity, delete_activity
from app.controllers.report import export_report_excel, export_report_pdf
from app.utils.pandas_model import PandasModel
from app.utils.plot_canvas import MplCanvas
import pandas as pd

BASE = Path(__file__).resolve().parents[0]
UI_DIR = BASE / "ui"

class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        uic.loadUi(str(UI_DIR / "login.ui"), self)
        self.btnLogin.clicked.connect(self.do_login)
        self.user = None

    def do_login(self):
        username = self.leUsername.text().strip()
        password = self.lePassword.text().strip()
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=?", (username,))
        row = cur.fetchone()
        conn.close()
        if row:
            # row['password'] is hashed — use verify from auth
            from app.controllers.auth import verify_password
            if verify_password(password, row['password']):
                self.user = {"id":row["id"], "username":row["username"], "role":row["role"], "nama":row["nama"]}
                self.accept()
                return
        QMessageBox.warning(self, "Login failed", "Username or password incorrect")

class RegisterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi(str(UI_DIR / "form_register.ui"), self)
        self.btnSave.clicked.connect(self.do_register)

    def do_register(self):
        nip = self.leNIP.text().strip()
        nama = self.leNama.text().strip()
        email = self.leEmail.text().strip()
        username = self.leUsername.text().strip()
        password = self.lePassword.text().strip()
        role = self.cmbRole.currentText()
        if not (nip and nama and email and username and password):
            QMessageBox.warning(self, "Error", "All fields are required")
            return
        try:
            register_user(nip, nama, email, username, password, role)
            QMessageBox.information(self, "OK", "User registered")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

class MainWindow(QMainWindow):
    def __init__(self, user):
        super().__init__()
        uic.loadUi(str(UI_DIR / "mainwindow.ui"), self)
        self.user = user
        # preview table model (import preview)
        self.preview_df = pd.DataFrame()
        self.model_preview = PandasModel(pd.DataFrame())
        self.tvPreview.setModel(self.model_preview)
        # report table
        self.model_report = PandasModel(pd.DataFrame())
        self.tvReport.setModel(self.model_report)
        # plot canvas
        self.canvas = MplCanvas(self.plotWidget, width=5, height=4, dpi=100)
        if self.plotWidget.layout() is None:
            self.plotWidget.setLayout(QVBoxLayout())
        self.plotWidget.layout().addWidget(self.canvas)
        # connect buttons
        self.btnBrowseFile.clicked.connect(self.browse_file)
        self.btnImport.clicked.connect(self.import_file_action)
        self.btnRunClustering.clicked.connect(self.run_clustering_action)
        self.btnExportExcel.clicked.connect(self.export_excel_action)
        self.btnExportPDF.clicked.connect(self.export_pdf_action)
        self.btnRegisterUser.clicked.connect(self.open_register_dialog)
        self.btnRefreshReport.clicked.connect(self.refresh_report_table)
        # hide register button if not admin
        if self.user['role'] != 'admin':
            self.btnRegisterUser.setVisible(False)
        self.load_filters()
        self.refresh_report_table()

    def browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Excel/CSV", "", "Excel Files (*.xlsx *.xls);;CSV Files (*.csv)")
        if not path: return
        self.lblFilePath.setText(path)
        df_preview, cols = preview_file(path)
        self.preview_df = pd.read_excel(path) if path.lower().endswith(('.xls','.xlsx')) else pd.read_csv(path)
        self.model_preview.update(self.preview_df.head(200))
        QMessageBox.information(self, "Preview", f"Preview loaded ({len(self.preview_df)} rows). Choose date filter then Import.")

    def import_file_action(self):
        path = self.lblFilePath.text().strip()
        if not path:
            QMessageBox.warning(self, "No file selected", "Please select a file first")
            return
        date_from = self.importFrom.date().toString("yyyy-MM-dd") if hasattr(self, 'importFrom') and self.importFrom.date() else None
        date_to = self.importTo.date().toString("yyyy-MM-dd") if hasattr(self, 'importTo') and self.importTo.date() else None
        date_filter = None
        if date_from and date_to:
            date_filter = (date_from, date_to)
        elif date_from:
            date_filter = date_from
        count = import_from_file(path, date_filter=date_filter)
        QMessageBox.information(self, "Import", f"{count} rows imported.")
        self.load_filters()
        self.refresh_report_table()

    def run_clustering_action(self):
        from app.models.clustering import run_kmeans_and_save
        res = run_kmeans_and_save()
        QMessageBox.information(self, "Clustering", f"Result: {res}")
        self.refresh_report_table()
        self.plot_clusters()

    def export_excel_action(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Excel", "report.xlsx", "Excel Files (*.xlsx)")
        if not path: return
        filters = self.get_filters()
        export_report_excel(path, filters)
        QMessageBox.information(self, "Saved", f"Saved to {path}")

    def export_pdf_action(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF", "report.pdf", "PDF Files (*.pdf)")
        if not path: return
        filters = self.get_filters()
        export_report_pdf(path, filters)
        QMessageBox.information(self, "Saved", f"Saved to {path}")

    def open_register_dialog(self):
        dlg = RegisterDialog(self)
        dlg.exec_()
        # after register, maybe refresh user list (if any UI)

    def load_filters(self):
        # load aplikasi list
        conn = get_connection()
        import pandas as pd
        df = pd.read_sql_query("SELECT DISTINCT aplikasi FROM aktivitas WHERE aplikasi IS NOT NULL", conn)
        conn.close()
        apps = ["All"] + df['aplikasi'].dropna().unique().tolist()
        self.cmbAplikasi.clear()
        self.cmbAplikasi.addItems(apps)
        self.cmbCluster.clear()
        self.cmbCluster.addItems(["All","1","2","3"])

    def get_filters(self):
        filters = {}
        if hasattr(self, 'reportFrom') and self.reportFrom.date():
            filters['date_from'] = self.reportFrom.date().toString("yyyy-MM-dd")
        if hasattr(self, 'reportTo') and self.reportTo.date():
            filters['date_to'] = self.reportTo.date().toString("yyyy-MM-dd")
        if self.cmbAplikasi.currentText() != "All":
            filters['aplikasi'] = self.cmbAplikasi.currentText()
        if self.cmbCluster.currentText() != "All":
            try:
                filters['cluster'] = int(self.cmbCluster.currentText())
            except:
                pass
        return filters

    def refresh_report_table(self):
        df = list_activities(self.get_filters())
        self.model_report.update(df)

    def plot_clusters(self):
        df = list_activities(self.get_filters())
        if df.empty:
            self.canvas.axes.clear()
            self.canvas.axes.set_title("No data")
            self.canvas.draw()
            return
        df2 = df.copy()
        df2['duration_minutes'] = df2['duration_minutes'].fillna(0)
        labels = df2['cluster'].fillna(0).astype(int)
        unique = labels.unique().tolist()
        mapping = {lab:i for i,lab in enumerate(unique)}
        colors = labels.map(mapping)
        self.canvas.axes.clear()
        self.canvas.axes.scatter(df2['id'], df2['duration_minutes'], c=colors)
        self.canvas.axes.set_xlabel("ID")
        self.canvas.axes.set_ylabel("Duration (minutes)")
        self.canvas.axes.set_title("Clustering Overview")
        for lab, idx in mapping.items():
            self.canvas.axes.scatter([], [], label=f"Cluster {lab}")
        self.canvas.axes.legend()
        self.canvas.draw()

def main():
    init_db()
    app = QApplication(sys.argv)
    login = LoginDialog()
    if login.exec_() == 1:
        mw = MainWindow(login.user)
        mw.show()
        sys.exit(app.exec_())

if __name__ == "__main__":
    main()
