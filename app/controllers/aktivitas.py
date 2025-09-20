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

def update_activity(id_, record: dict):
    conn = get_connection()
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
        id_
    ))
    conn.commit()
    conn.close()

def delete_activity(id_):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM aktivitas WHERE id=?", (id_,))
    conn.commit()
    conn.close()

def list_activities(filters=None):
    conn = get_connection()
    q = "SELECT * FROM aktivitas WHERE 1=1"
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
