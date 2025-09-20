# app/models/clustering.py
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from .db import get_connection

def run_kmeans_and_save():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM aktivitas", conn)
    if df.empty:
        conn.close()
        return {"status":"empty"}
    df['duration_minutes'] = df['duration_minutes'].fillna(0).astype(int)
    # mark tertunda = 3
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
        mapping[sorted_labels[-1]] = 2
    # update DB
    for _, row in active.iterrows():
        cluster_value = mapping.get(row['klabel'], 1)
        cur.execute("UPDATE aktivitas SET cluster = ? WHERE id = ?", (int(cluster_value), int(row['id'])))
    conn.commit()
    conn.close()
    return {"status":"ok", "count_active": active.shape[0]}
