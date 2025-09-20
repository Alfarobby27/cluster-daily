## How to contribute

1. Clone repo

```bash
git clone https://github.com/Alfarobby27/cluster-daily.git && cd cluster-daily
```

2. Create virtual Environment

```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

### Tutorial yang saya ikuti sebelumnya (Koreksi jika salah)

Tutorial Lengkap: Buat Aplikasi Desktop ClusterDaily (CRUD, Import Excel, Scheduling, K-Means, Register User, Report) — dari 0 sampai jadi installer
Saya susun langkah demi langkah, file-by-file, termasuk kode lengkap yang bisa Anda copy–paste. Tutorial ini ditargetkan supaya Anda bisa langsung mengikuti (Windows contoh), aplikasi aman (password hashed), responsif (threading), terukur (K-Means), dan bisa dibuat installer (PyInstaller + Inno Setup).
Catatan: saya gunakan struktur project cluster-daily/ dengan folder source app/ di dalamnya. Sesuaikan path kalau Anda memilih nama lain.

---

0 — Ringkasan singkat output akhir
Aplikasi desktop (PyQt5) yang bisa:
• Login (role: admin, leader, programmer)
• Admin dapat register user (NIP, nama, email, username, password, role)
• CRUD aktivitas (form), Import Excel/CSV (preview → pilih tanggal/rentang → import)
• Hitung durasi otomatis (start_scheduler → finish_bridge)
• Jalankan K-Means (3 kategori: Ringan / Berat / Tertunda)
• Filter & export report (Excel, PDF) berdasarkan rentang tanggal, aplikasi, cluster
• Packaging → single .exe dan installer .exe

---

1 — Persiapan & struktur folder (Windows contoh)
Buat folder project:

```bash
C:\Users\<you>\projects\cluster-daily\ <-- root
Struktur ideal:
cluster-daily/
├─ venv/ # virtual environment
├─ app/ # source code
│ ├─ main.py
│ ├─ ui/ # .ui files (Qt Designer)
│ │ ├─ login.ui
│ │ ├─ mainwindow.ui
│ │ ├─ form_register.ui
│ │ ├─ form_aktivitas.ui
│ │ └─ import_preview.ui
│ ├─ models/
│ │ ├─ db.py
│ │ ├─ importer.py
│ │ └─ clustering.py
│ ├─ controllers/
│ │ ├─ auth.py
│ │ ├─ aktivitas.py
│ │ └─ report.py
│ ├─ utils/
│ │ ├─ pandas_model.py
│ │ ├─ plot_canvas.py
│ │ └─ export_pdf.py
│ ├─ views/ # optional converted .ui -> .py
│ └─ data/
│ └─ aktivitas.db
├─ requirements.txt
└─ README.md

```

---

2 — Buat virtual environment & install dependency
Buka PowerShell (Windows) di folder cluster-daily:

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install pyqt5 pandas numpy scikit-learn matplotlib openpyxl reportlab bcrypt pyinstaller
pip freeze > requirements.txt
Jalankan pip freeze > requirements.txt di root cluster-daily setelah venv aktif — supaya file hanya berisi paket project.
```

---

3 — Database: app/models/db.py
Buat file app/models/db.py (lengkap, with indexes, backup helper):

```bash
# app/models/db.py

import sqlite3
from pathlib import Path
from datetime import datetime
import shutil

BASE = Path(**file**).resolve().parents[2] / "app"
DATA_DIR = BASE / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "aktivitas.db"

def get_connection():
conn = sqlite3.connect(str(DB_PATH), detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
conn.row_factory = sqlite3.Row
return conn

def init_db():
conn = get_connection()
cur = conn.cursor() # users
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
id INTEGER PRIMARY KEY AUTOINCREMENT,
nip TEXT UNIQUE,
nama TEXT,
email TEXT UNIQUE,
username TEXT UNIQUE,
password TEXT,
role TEXT CHECK(role IN ('admin','leader','programmer')) NOT NULL
)
""") # aktivitas
cur.execute("""
CREATE TABLE IF NOT EXISTS aktivitas (
id INTEGER PRIMARY KEY AUTOINCREMENT,
tanggal TEXT,
aplikasi TEXT,
depo TEXT,
tipe TEXT,
collection TEXT,
object TEXT,
start_scheduler TEXT,
finish_scheduler TEXT,
start_bridge TEXT,
finish_bridge TEXT,
duration_minutes INTEGER,
status TEXT,
notes TEXT,
scheduled_at TEXT,
cluster INTEGER
)
""") # Indexes for performance
cur.execute("CREATE INDEX IF NOT EXISTS idx_aktivitas_tanggal ON aktivitas(tanggal)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_aktivitas_cluster ON aktivitas(cluster)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
conn.commit() # insert default admin if none
cur.execute("SELECT COUNT(\*) as c FROM users")
if cur.fetchone()["c"] == 0: # default admin: username admin, password admin123 (hashed later by auth module if needed)
cur.execute("INSERT INTO users (nip,nama,email,username,password,role) VALUES (?,?,?,?,?,?)",
("000000", "Administrator", "admin@example.com", "admin", "admin123", "admin"))
conn.commit()
conn.close()

def backup*db():
"""Simple DB backup: copy with timestamp"""
ts = datetime.now().strftime("%Y%m%d*%H%M%S")
backup*path = DATA_DIR / f"aktivitas_backup*{ts}.db"
shutil.copy2(DB_PATH, backup_path)
return str(backup_path)

if **name** == "**main**":
init_db()
print("DB initialized at", DB_PATH)
Jalankan python -c "from app.models.db import init_db; init_db()" sekali untuk buat DB.
```

---

4 — Security: Password hashing helpers app/controllers/auth.py
Buat app/controllers/auth.py dengan bcrypt hashing and RBAC:

```bash

# app/controllers/auth.py

from app.models.db import get_connection
import bcrypt
from typing import Optional

def hash_password(password: str) -> str:
return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
try:
return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
except Exception:
return False

def authenticate(username: str, password: str) -> Optional[dict]:
conn = get_connection()
cur = conn.cursor()
cur.execute("SELECT \* FROM users WHERE username=?", (username,))
row = cur.fetchone()
conn.close()
if row and verify_password(password, row["password"]):
return {"id": row["id"], "username":row["username"], "role":row["role"], "nama":row["nama"], "nip":row["nip"], "email":row["email"]}
return None

def register_user(nip, nama, email, username, password, role):
if role not in ("admin","leader","programmer"):
raise ValueError("Invalid role")
hashed = hash_password(password)
conn = get_connection()
cur = conn.cursor()
try:
cur.execute("""
INSERT INTO users (nip,nama,email,username,password,role)
VALUES (?,?,?,?,?,?)
""", (nip, nama, email, username, hashed, role))
conn.commit()
finally:
conn.close()
Important: When you create default admin in db.py you stored a plain password; you can update it to hashed by calling register_user manually or replace the default insertion with hashed. For now after first run, replace default admin password by re-registering.

```

---

5 — Importer in-app (app/models/importer.py)
This module is called from UI when user selects file and presses Import. It previews and imports with date filter.

```bash
# app/models/importer.py

import pandas as pd
import re
from datetime import datetime, timedelta, time
from .db import get_connection
import numpy as np

def parse_time_value(val, ref_date=None):
if pd.isna(val):
return None
if isinstance(val, datetime):
return val
s = str(val).strip() # duration-like "1 jam 32 menit 20 detik" -> convert to datetime offset from midnight
if 'jam' in s or 'menit' in s:
hours = int(re.search(r'(\d+)\s*jam', s).group(1)) if re.search(r'(\d+)\s*jam', s) else 0
mins = int(re.search(r'(\d+)\s*menit', s).group(1)) if re.search(r'(\d+)\s*menit', s) else 0
secs = int(re.search(r'(\d+)\s*detik', s).group(1)) if re.search(r'(\d+)\s*detik', s) else 0
if ref_date is None:
ref_date = datetime.today()
return datetime.combine(ref_date.date(), time(0,0)) + timedelta(hours=hours, minutes=mins, seconds=secs)
s2 = s.replace('.',':').replace(',',':')
for fmt in ("%H:%M:%S","%H:%M","%H"):
try:
t = datetime.strptime(s2, fmt).time()
if ref_date is None: ref_date = datetime.today()
return datetime.combine(ref_date.date(), t)
except:
pass
try:
num = float(s)
if 0 < num < 1:
secs = int(num * 24*3600)
if ref_date is None: ref_date = datetime.today()
return datetime.combine(ref_date.date(), time(0,0)) + timedelta(seconds=secs)
except:
pass
return None

def adjust_finish(start_dt, finish_dt):
if start_dt and finish_dt and finish_dt < start_dt:
return finish_dt + timedelta(days=1)
return finish_dt

def preview_file(path, sheet_name=None, nrows=200):
if path.lower().endswith('.csv'):
df = pd.read_csv(path)
else:
df = pd.read_excel(path, sheet_name=sheet_name)
return df.head(nrows), list(df.columns)

def import_from_file(path, sheet_name=None, date_filter=None):
"""
date_filter: None | 'YYYY-MM-DD' | (from,to) as strings
Returns number of rows inserted
"""
if path.lower().endswith('.csv'):
df = pd.read_csv(path)
else:
df = pd.read_excel(path, sheet_name=sheet_name)

    # lower-case mapping keys
    cols_map = {c.lower().strip(): c for c in df.columns}
    def col(names):
        for k in names:
            if k in cols_map:
                return cols_map[k]
        return None

    col_date = col(['tanggal','date'])
    col_app = col(['aplikasi','app','application'])
    col_start_scheduler = col(['start scheduler','start_scheduler','start_scheduler'])
    col_finish_scheduler = col(['scheduller finish','finish scheduler','finish_scheduler'])
    col_start_bridge = col(['start bridge','start_bridge','start bridge','start birdge'])
    col_finish_bridge = col(['finish bridge','finish_bridge'])
    col_status = col(['status'])
    col_notes = col(['notes','keterangan','note'])

    conn = get_connection()
    cur = conn.cursor()
    rows = 0
    # Use transaction for speed & reliability
    cur.execute("BEGIN")
    for _, row in df.iterrows():
        # parse date if exists
        tanggal_dt = None
        if col_date and not pd.isna(row.get(col_date)):
            try:
                tanggal_dt = pd.to_datetime(row.get(col_date))
            except:
                tanggal_dt = None
        # date filter
        if date_filter:
            if isinstance(date_filter, tuple):
                if tanggal_dt is None:
                    continue
                if not (pd.to_datetime(date_filter[0]) <= tanggal_dt <= pd.to_datetime(date_filter[1])):
                    continue
            else:
                if tanggal_dt is None:
                    continue
                if pd.to_datetime(date_filter) != tanggal_dt.normalize():
                    continue

        ref_date = tanggal_dt if tanggal_dt is not None else datetime.today()
        ss = parse_time_value(row.get(col_start_scheduler), ref_date)
        fs = parse_time_value(row.get(col_finish_scheduler), ref_date)
        sb = parse_time_value(row.get(col_start_bridge), ref_date)
        fb = parse_time_value(row.get(col_finish_bridge), ref_date)

        fs = adjust_finish(ss, fs)
        fb = adjust_finish(ss, fb)

        duration_minutes = 0
        if ss and fb:
            duration_minutes = int((fb - ss).total_seconds() // 60)
            if duration_minutes < 0:
                duration_minutes = 0

        cur.execute("""
            INSERT INTO aktivitas (
                tanggal, aplikasi, start_scheduler, finish_scheduler,
                start_bridge, finish_bridge, duration_minutes, status, notes
            ) VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            tanggal_dt.strftime("%Y-%m-%d") if tanggal_dt is not None else None,
            row.get(col_app) if col_app else None,
            ss.isoformat() if ss else None,
            fs.isoformat() if fs else None,
            sb.isoformat() if sb else None,
            fb.isoformat() if fb else None,
            duration_minutes,
            row.get(col_status) if col_status else None,
            row.get(col_notes) if col_notes else None
        ))
        rows += 1
    cur.execute("COMMIT")
    conn.close()
    return rows

```

---

6 — K-Means clustering (app/models/clustering.py)

```bash
# app/models/clustering.py

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from .db import get_connection

def run*kmeans_and_save():
conn = get_connection()
df = pd.read_sql_query("SELECT \* FROM aktivitas", conn)
if df.empty:
conn.close()
return {"status":"empty"}
df['duration_minutes'] = df['duration_minutes'].fillna(0).astype(int) # mark tertunda = 3
cur = conn.cursor()
cur.execute("UPDATE aktivitas SET cluster = 3 WHERE duration_minutes = 0")
conn.commit()
active = df[df['duration_minutes'] > 0].copy()
if active.shape[0] == 0:
conn.close()
return {"status":"only_tertunda"}
X = active[['duration_minutes']].values.astype(float)
scaler = StandardScaler()
Xs = scaler.fit_transform(X)
k = 2 if active.shape[0] >= 2 else 1
kmeans = KMeans(n_clusters=k, random_state=42, n_init="auto")
labels = kmeans.fit_predict(Xs)
active['klabel'] = labels
means = active.groupby('klabel')['duration_minutes'].mean().sort_values()
sorted_labels = list(means.index)
mapping = {}
if len(sorted_labels) == 1:
mapping[sorted_labels[0]] = 1
else:
mapping[sorted_labels[0]] = 1
mapping[sorted_labels[-1]] = 2 # update DB
for *, row in active.iterrows():
cluster_value = mapping.get(row['klabel'], 1)
cur.execute("UPDATE aktivitas SET cluster = ? WHERE id = ?", (int(cluster_value), int(row['id'])))
conn.commit()
conn.close()
return {"status":"ok", "count_active": active.shape[0]}

```

---

7 — CRUD Controller (app/controllers/aktivitas.py)

```bash
# app/controllers/aktivitas.py

from app.models.db import get_connection
import pandas as pd

def insert_activity(record: dict):
conn = get_connection()
cur = conn.cursor()
cur.execute("""
INSERT INTO aktivitas (
tanggal, aplikasi, depo, tipe, collection, object,
start_scheduler, finish_scheduler, start_bridge, finish_bridge,
duration_minutes, status, notes, scheduled_at
) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
""", (
record.get('tanggal'),
record.get('aplikasi'),
record.get('depo'),
record.get('tipe'),
record.get('collection'),
record.get('object'),
record.get('start_scheduler'),
record.get('finish_scheduler'),
record.get('start_bridge'),
record.get('finish_bridge'),
record.get('duration_minutes'),
record.get('status'),
record.get('notes'),
record.get('scheduled_at')
))
conn.commit()
conn.close()

def update*activity(id*, record: dict):
conn = get*connection()
cur = conn.cursor()
cur.execute("""
UPDATE aktivitas SET
tanggal=?, aplikasi=?, depo=?, tipe=?, collection=?, object=?,
start_scheduler=?, finish_scheduler=?, start_bridge=?, finish_bridge=?, duration_minutes=?, status=?, notes=?, scheduled_at=?
WHERE id=?
""", (
record.get('tanggal'),
record.get('aplikasi'),
record.get('depo'),
record.get('tipe'),
record.get('collection'),
record.get('object'),
record.get('start_scheduler'),
record.get('finish_scheduler'),
record.get('start_bridge'),
record.get('finish_bridge'),
record.get('duration_minutes'),
record.get('status'),
record.get('notes'),
record.get('scheduled_at'),
id*
))
conn.commit()
conn.close()

def delete*activity(id*):
conn = get*connection()
cur = conn.cursor()
cur.execute("DELETE FROM aktivitas WHERE id=?", (id*,))
conn.commit()
conn.close()

def list_activities(filters=None):
conn = get_connection()
q = "SELECT \* FROM aktivitas WHERE 1=1"
params = []
if filters:
if filters.get('date_from'):
q += " AND tanggal >= ?"
params.append(filters['date_from'])
if filters.get('date_to'):
q += " AND tanggal <= ?"
params.append(filters['date_to'])
if filters.get('aplikasi'):
q += " AND aplikasi = ?"
params.append(filters['aplikasi'])
if filters.get('cluster'):
q += " AND cluster = ?"
params.append(filters['cluster'])
q += " ORDER BY tanggal DESC, id DESC"
df = pd.read_sql_query(q, conn, params=params)
conn.close()
return df
```

---

8 — Report utilities: app/utils/export_pdf.py and app/controllers/report.py

```bash
app/utils/export_pdf.py:

# app/utils/export_pdf.py

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

def export*df_to_pdf(df, file_path, title="Report"):
doc = SimpleDocTemplate(file_path, pagesize=A4)
style = getSampleStyleSheet()
elems = [Paragraph(title, style['Title']), Spacer(1,12)]
data = [list(df.columns)]
for *, row in df.iterrows():
data.append([str(x) for x in row.tolist()])
table = Table(data, repeatRows=1)
table.setStyle(TableStyle([
('BACKGROUND',(0,0),(-1,0),colors.grey),
('GRID',(0,0),(-1,-1),0.25,colors.black),
('VALIGN',(0,0),(-1,-1),'TOP'),
]))
elems.append(table)
doc.build(elems)
app/controllers/report.py:

# app/controllers/report.py

from app.controllers.aktivitas import list_activities
from app.utils.export_pdf import export_df_to_pdf

def export_report_excel(path, filters=None):
df = list_activities(filters)
df.to_excel(path, index=False)

def export_report_pdf(path, filters=None, title="Activity Report"):
df = list_activities(filters)
export_df_to_pdf(df, path, title)
```

---

9 — UI utilities: PandasModel & PlotCanvas (app/utils/pandas_model.py, app/utils/plot_canvas.py)

```bash
app/utils/pandas_model.py:

# app/utils/pandas_model.py

from PyQt5.QtCore import QAbstractTableModel, Qt, QVariant

class PandasModel(QAbstractTableModel):
def **init**(self, df=None):
super().**init**()
self.\_df = df

    def update(self, df):
        self.beginResetModel()
        self._df = df
        self.endResetModel()

    def rowCount(self, parent=None):
        return 0 if self._df is None else len(self._df.index)

    def columnCount(self, parent=None):
        return 0 if self._df is None else len(self._df.columns)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or self._df is None:
            return QVariant()
        if role == Qt.DisplayRole:
            val = self._df.iat[index.row(), index.column()]
            return str(val)
        return QVariant()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if self._df is None:
            return QVariant()
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._df.columns[section])
            else:
                return str(self._df.index[section])
        return QVariant()
```

```bash
app/utils/plot_canvas.py:


# app/utils/plot_canvas.py

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class MplCanvas(FigureCanvas):
def **init**(self, parent=None, width=5, height=4, dpi=100):
fig = Figure(figsize=(width, height), dpi=dpi)
self.axes = fig.add_subplot(111)
super().**init**(fig)
```

---

10 — Main application (UI binding) app/main.py
Ini file skeleton lengkap yang menggabungkan login, main window, import, clustering, register user. Pastikan objectNames di .ui sesuai (saya tulis nama widget yang dipakai).

```bash
# app/main.py

import sys
from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow, QDialog, QFileDialog, QMessageBox, QVBoxLayout
from pathlib import Path
from app.models.db import init_db, get_connection
from app.models.importer import preview_file, import_from_file
from app.controllers.clustering import run_kmeans_and_save as clustering_run
from app.controllers.auth import authenticate, register_user
from app.controllers.aktivitas import list_activities, insert_activity, update_activity, delete_activity
from app.controllers.report import export_report_excel, export_report_pdf
from app.utils.pandas_model import PandasModel
from app.utils.plot_canvas import MplCanvas
import pandas as pd

BASE = Path(**file**).resolve().parents[0]
UI_DIR = BASE / "ui"

class LoginDialog(QDialog):
def **init**(self):
super().**init**()
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
def **init**(self, parent=None):
super().**init**(parent)
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
def **init**(self, user):
super().**init**()
uic.loadUi(str(UI_DIR / "mainwindow.ui"), self)
self.user = user # preview table model (import preview)
self.preview_df = pd.DataFrame()
self.model_preview = PandasModel(pd.DataFrame())
self.tvPreview.setModel(self.model_preview) # report table
self.model_report = PandasModel(pd.DataFrame())
self.tvReport.setModel(self.model_report) # plot canvas
self.canvas = MplCanvas(self.plotWidget, width=5, height=4, dpi=100)
if self.plotWidget.layout() is None:
self.plotWidget.setLayout(QVBoxLayout())
self.plotWidget.layout().addWidget(self.canvas) # connect buttons
self.btnBrowseFile.clicked.connect(self.browse_file)
self.btnImport.clicked.connect(self.import_file_action)
self.btnRunClustering.clicked.connect(self.run_clustering_action)
self.btnExportExcel.clicked.connect(self.export_excel_action)
self.btnExportPDF.clicked.connect(self.export_pdf_action)
self.btnRegisterUser.clicked.connect(self.open_register_dialog)
self.btnRefreshReport.clicked.connect(self.refresh_report_table) # hide register button if not admin
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
init*db()
app = QApplication(sys.argv)
login = LoginDialog()
if login.exec*() == 1:
mw = MainWindow(login.user)
mw.show()
sys.exit(app.exec\_())

if **name** == "**main**":
main()
Perhatian: object names seperti btnBrowseFile, tvPreview, importFrom, importTo, btnRegisterUser, dll harus ada pada mainwindow.ui Anda. Jika Anda convert .ui → .py, sesuaikan imports.
```

---

11 — Qt Designer: bikin .ui (panduan cepat)
Di Qt Designer buat:
• login.ui: leUsername, lePassword, btnLogin
• form_register.ui: fields leNIP, leNama, leEmail, leUsername, lePassword, cmbRole, btnSave
• mainwindow.ui: layout dengan widgets: lblFilePath, btnBrowseFile, tvPreview, importFrom, importTo, btnImport, btnRunClustering, btnExportExcel, btnExportPDF, tvReport, plotWidget, cmbAplikasi, cmbCluster, btnRegisterUser, btnRefreshReport, etc.
Simpan .ui ke app/ui/. Anda bisa load .ui langsung via uic.loadUi() seperti contoh main.py.

---

12 — Threading (agar UI tidak freeze saat import / clustering)
Gunakan QThread worker pattern. Contoh singkat:

```bash
# app/utils/worker.py

from PyQt5.QtCore import QThread, pyqtSignal

class WorkerThread(QThread):
finished = pyqtSignal(object) # send result or status
progress = pyqtSignal(int)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit({"error": str(e)})
```

Gunakan ini di MainWindow untuk menjalankan import_from_file dan run_kmeans_and_save di background.

---

13 — Backup & Reliability
Pada setiap import action, panggil backup_db() dari db.py untuk menyimpan salinan DB sebelum insert. Hal ini meminimalkan risiko kehilangan data.
Contoh:

```bash
from app.models.db import backup_db
backup_db()
count = import_from_file(path, date_filter=date_filter)
```

---

14 — Packaging: PyInstaller (Windows)

1. Pastikan app berjalan saat python app/main.py.
2. Build exe (jalankan di root cluster-daily dengan venv aktif):

# windows: note add-data uses semicolon ; inside quotes and relative paths

pyinstaller --noconfirm --onefile --windowed --add-data "app/ui;app/ui" --add-data "app/data;app/data" --name ClusterDaily app/main.py 3. Output: dist/ClusterDaily.exe. Test exe di mesin. 4. Jika ada missing imports (PyInstaller warnings), tambahkan --hidden-import flags.

---

15 — Membuat installer Windows (Inno Setup)
Contoh ClusterDaily.iss:

```bash
[Setup]
AppName=ClusterDaily
AppVersion=1.0
DefaultDirName={pf}\ClusterDaily
DefaultGroupName=ClusterDaily
OutputBaseFilename=ClusterDailyInstaller
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\ClusterDaily.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "app\data\*"; DestDir: "{app}\data"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\ClusterDaily"; Filename: "{app}\ClusterDaily.exe"
Name: "{commondesktop}\ClusterDaily"; Filename: "{app}\ClusterDaily.exe"
Compile .iss di Inno Setup Compiler → hasil ClusterDailyInstaller.exe.
```

---

16 — Testing checklist sebelum submit atau presentasi
• Jalankan python app/main.py → login admin (use created admin)
• Admin → Register new user (nip, nama, email, username, password, role) → login with new user
• Import Excel/CSV via Import page → preview → choose date range → import → DB updated
• CRUD add/edit/delete activity via form
• Run Clustering → check DB cluster values (1/2/3)
• Filter report, export Excel, export PDF → verify files
• Test exe (dist) on target machine (without Python installed)
• Test installer produced by Inno Setup (install/uninstall)

---

17 — Teks K-Means yang bisa Anda masukkan ke skripsi (BAB III / BAB IV)
Copy−paste ready-to-use (edit kata-kata sesuai gaya Anda):
Penerapan K-Means Clustering
Untuk setiap aktivitas, kami menghitung durasi total did_i dalam menit sebagai selisih antara finish_bridge dan start_scheduler. Observasi dengan durasi nol (di=0d_i = 0) dikategorikan langsung sebagai Aktivitas Tertunda. Untuk observasi lain digunakan algoritma K-Means dengan langkah:

1. Standardisasi fitur durasi menggunakan StandardScaler sehingga mean = 0 dan var = 1.
2. Jalankan K-Means dengan k=2k=2 pada data non-zero untuk memisahkan Ringan dan Berat.
3. Mapping cluster ke label berdasarkan rata-rata durasi tiap cluster: cluster dengan mean lebih rendah diberi label Ringan, cluster dengan mean lebih tinggi diberi label Berat.
4. Simpan hasil cluster ke basis data untuk keperluan visualisasi dan laporan.
   Fungsi objektif K-Means:
   min⁡S∑j=1k∑x∈Sj∥x−μj∥2\min*{S}\sum*{j=1}^{k}\sum\_{x\in S_j}\|x-\mu_j\|^2
   dengan μj\mu_j centroid cluster SjS_j. Evaluasi kualitas clustering dapat menggunakan inertia dan silhouette score.

---

18 — Tips praktis & best practices (PSRUP)
• Performance: gunakan indexes, batch insert (transaction), minimalisasi pembacaan DB berulang.
• Security: hash password (bcrypt), validasi input (email regex, password policy), RBAC checks di UI & controller.
• Reliability: DB backup before import, robust try/except, logging (module logging) ke file app/logs/app.log.
• Usability: preview import, confirm dialogs for delete, progress bar for long tasks, keyboard shortcuts, responsive UI (threads).
• Portability: relative paths (Pathlib), include data/ and ui/ in PyInstaller add-data.

---

19 — Files saya sarankan Anda buat sekarang (urutan)

1. app/models/db.py → jalankan init_db()
2. app/controllers/auth.py & update default admin password with hashed one: call register_user(...) for admin, or change DB default.
3. app/models/importer.py → test preview_file() in REPL and import_from_file() from small test file.
4. app/models/clustering.py → test run_kmeans_and_save after inserting sample rows.
5. Create .ui files in Qt Designer (login, mainwindow, form_register, import_preview).
6. app/main.py → run app.
7. Add worker threading for heavy operations.
8. Build exe & installer.

---

20 — Saya bantu langkah demi langkah sekarang (opsional)
Saya bisa langsung kirimkan file-by-file (kode lengkap yang tadi dirangkum) agar Anda tinggal membuat file .py sesuai path. Saya juga bisa kirimkan XML .ui untuk login.ui & mainwindow.ui agar langsung buka di Qt Designer.
Pilih salah satu:
• A: Kirimkan semua file .py lengkap (copy–paste ready).
• B: Kirimkan file .ui (XML) untuk login & mainwindow.
• C: Langkah demi langkah saya temani — kita buat file per file dan Anda jalankan di PC (saya berikan perintah yang harus Anda jalankan).
Sebut A, B, atau C — saya akan kirim langsung.
