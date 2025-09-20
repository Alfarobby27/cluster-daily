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
    s = str(val).strip()
    # duration-like "1 jam 32 menit 20 detik" -> convert to datetime offset from midnight
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
