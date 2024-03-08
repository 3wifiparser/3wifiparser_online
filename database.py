import sqlite3
import os
import random
import string
from threading import Lock
import logging
from time import time
from utils import json_lib as json
from datetime import datetime
from utils import Task

conn = None
db_lock = Lock()

drop_tables = "DROP TABLE IF EXISTS \"networks\";\nDROP TABLE IF EXISTS \"tasks\";"
create_tables = """CREATE TABLE IF NOT EXISTS "networks" (
	"SSID"	TEXT,
	"BSSID"	TEXT,
	"format"	INTEGER,
	"sec"	TEXT,
	"passwords"	TEXT,
	"WPS_keys"	TEXT,
	"lat"	REAL,
	"lon"	REAL,
	"time"	INTEGER,
	"local_id"	INTEGER,
	"scanned_time"	INTEGER,
    "shared"	INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS "tasks" (
	"id"	INTEGER,
	"progress"	INTEGER,
	"pos"	TEXT,
	"z"	INTEGER,
	"min_maxTileX"	TEXT,
	"min_maxTileY"	TEXT,
	"max_area"	INTEGER,
	PRIMARY KEY("id" AUTOINCREMENT)
);"""

def init_temp_db():
    global conn
    if not(os.path.isdir("tempdbs")):
        os.mkdir("tempdbs")
    rand_database_id = "".join(random.choices(string.ascii_letters, k=5))
    conn = sqlite3.connect(f"tempdbs/temp{rand_database_id}.db", check_same_thread=False)
    cur = conn.cursor()
    cur.executescript(drop_tables + create_tables)
    cur.close()
    conn.commit()


def load_db(path):
    global conn
    conn = sqlite3.connect(path, check_same_thread=False)
    cur = conn.cursor()
    cur.executescript(create_tables)
    cur.close()
    conn.commit()

def save_networks(data, subtask):
    global conn
    if conn == None:
        init_temp_db()
    db_lock.acquire()
    cur = conn.cursor()
    for i in range(10):
        try:
            cur.executemany(f"INSERT INTO networks (SSID, BSSID, lat, lon, local_id) VALUES ((?),(?),(?),(?),{subtask})", data)
            conn.commit()
            break
        except Exception:
            retry_index = f"### RETRY {i}: " if i > 0 else ""
            logging.exception(f"{retry_index}database.save_networks exception")
    cur.close()
    db_lock.release()

def save_passwords_ajax(data):
    global conn
    if conn == None:
        init_temp_db()
    psd_data = []
    for net,bssid in data:
        psd = [None, None, bssid]
        if not(net.get("Successes")):
            psd_data.append(psd)
            continue
        psd[0] = json.dumps(net["Keys"])[1:-1]
        psd[1] = json.dumps(net["WPS"])[1:-1]
        psd_data.append(psd)
    db_lock.acquire()
    cur = conn.cursor()
    for i in range(10):
        try:
            cur.executemany(f"UPDATE networks SET format=0,sec=NULL,passwords=?,WPS_keys=?,time=NULL WHERE BSSID=?", psd_data)
            conn.commit()
            break
        except Exception:
            logging.exception("database.save_passwords_ajax exception")
    cur.close()
    db_lock.release()

def convert_date_to_unix(date_string):
    dt = datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")
    return int(dt.timestamp())

def save_passwords_gate(data):
    global conn
    if conn == None:
        init_temp_db()
    db_lock.acquire()
    cur = conn.cursor()
    for bssid, wifi_list in data.items():
        wifi_list.sort(key=lambda a: convert_date_to_unix(a["time"]))
        cur.execute("UPDATE networks SET format=-1 WHERE BSSID=? AND format is NULL", (bssid, ))
        for wifi_info in wifi_list:
            essid = wifi_info["essid"]
            sec = wifi_info["sec"]
            key = wifi_info["key"]
            wps = wifi_info["wps"]
            tim = wifi_info["time"]
            cur.execute(f"""UPDATE networks SET format=1,sec=?,passwords=?,WPS_keys=?,time=?
            WHERE ROWID IN (
                SELECT ROWID FROM networks WHERE BSSID=? AND SSID=? AND format=-1 LIMIT 1
            )""", (sec, key, wps, tim, bssid, essid))
    cur.close()
    conn.commit()
    db_lock.release()

def update_task(task: Task, progress: int):
    db_lock.acquire()
    cur = conn.cursor()
    cur.execute("UPDATE tasks SET progress=? WHERE id=?", (progress, task.local_id))
    cur.close()
    conn.commit()
    db_lock.release()

def create_task(task: Task):
    db_lock.acquire()
    cur = conn.cursor()
    cur.execute("INSERT INTO tasks VALUES (NULL,0,\"[0,0]\",17,?,?,?);", (json.dumps(task.min_maxTileX), json.dumps(task.min_maxTileY),task.max_area))
    cur.execute("SELECT id FROM tasks WHERE ROWID=?", (cur.lastrowid, ))
    task.local_id = cur.fetchone()[0]
    cur.close()
    conn.commit()
    db_lock.release()

def _fetchone(query:str, params=()):
    global conn
    if conn == None:
        init_temp_db()
    db_lock.acquire()
    cur = conn.cursor()
    cur.execute(query, params)
    data = cur.fetchone()[0]
    cur.close()
    db_lock.release()
    return data

def _fetchall(query:str, params=()):
    global conn
    if conn == None:
        init_temp_db()
    db_lock.acquire()
    cur = conn.cursor()
    cur.execute(query, params)
    data = cur.fetchall()
    cur.close()
    db_lock.release()
    return data

def get_cnt_null_pass():
    return _fetchone("SELECT count(*) FROM networks WHERE format IS NULL")

def get_bssids_tb(all_queued, limit):
    return _fetchall("SELECT DISTINCT bssid FROM networks WHERE format IS NULL AND bssid NOT in (?) LIMIT (?)", (str(all_queued)[1:-1], limit))

def get_null_passwords_bssids(limit):
    return _fetchall("SELECT DISTINCT bssid FROM networks WHERE format IS NULL LIMIT (?)", (limit, ))

def get_nets(subtask):
    return _fetchall("SELECT SSID,BSSID,format,sec,passwords,WPS_keys,lat,lon,time FROM networks WHERE local_id=?", (subtask, ))

def get_total_nets():
    return _fetchone("SELECT max(ROWID) FROM networks;")

def get_non_shared():
    return _fetchall("SELECT SSID,BSSID,format,sec,passwords,WPS_keys,lat,lon,time FROM networks WHERE shared=0 AND NOT(format IS NULL) LIMIT 800")

def get_task(task_id):
    data = _fetchall("SELECT * FROM tasks WHERE id=?", (task_id, ))
    if len(data) < 1:
        raise Exception("Wrong task ID")
    data = data[0]
    task = Task()
    task.local_id = data[0]
    task.progress = [int(data[1]), 67108864]
    task.min_maxTileX = json.loads(data[4])
    task.min_maxTileY = json.loads(data[5])
    task.max_area = int(data[6])
    return task

def set_shared(bssids):
    global conn
    if conn == None:
        init_temp_db()
    db_lock.acquire()
    cur = conn.cursor()
    cur.execute(f"UPDATE networks SET shared=1 WHERE bssid IN ({str(bssids)[1:-1]});")
    cur.close()
    conn.commit()
    db_lock.release()