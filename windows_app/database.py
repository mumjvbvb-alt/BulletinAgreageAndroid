import sqlite3, json, shutil, zipfile
from pathlib import Path
from datetime import datetime

SCHEMA="""
CREATE TABLE IF NOT EXISTS invoices(
 id INTEGER PRIMARY KEY AUTOINCREMENT, bon_number INTEGER UNIQUE NOT NULL,
 invoice_date TEXT NOT NULL, species TEXT NOT NULL, producer TEXT, address TEXT,
 producer_id TEXT, agreer TEXT, quantity_qx REAL, collection_point TEXT,
 status TEXT NOT NULL, reason TEXT, data_json TEXT NOT NULL, layout_json TEXT NOT NULL,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS producers(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT UNIQUE NOT NULL,address TEXT,identity_number TEXT);
CREATE TABLE IF NOT EXISTS reasons(id INTEGER PRIMARY KEY AUTOINCREMENT,category TEXT NOT NULL,reason TEXT NOT NULL,UNIQUE(category,reason));
CREATE TABLE IF NOT EXISTS app_settings(key TEXT PRIMARY KEY,value TEXT);
"""

class Database:
    def __init__(self,path):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        self.conn=sqlite3.connect(self.path); self.conn.row_factory=sqlite3.Row
        self.conn.executescript(SCHEMA); self.conn.commit()
    def setting(self,key,default=None):
        x=self.conn.execute("SELECT value FROM app_settings WHERE key=?",(key,)).fetchone()
        return x["value"] if x else default
    def save_setting(self,key,value):
        self.conn.execute("INSERT INTO app_settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(key,str(value))); self.conn.commit()
    def next_bon(self):
        x=self.conn.execute("SELECT COALESCE(MAX(bon_number),0)+1 n FROM invoices").fetchone(); return int(x["n"])
    def save_producer(self,name,address,identity):
        self.conn.execute("INSERT INTO producers(name,address,identity_number) VALUES(?,?,?) ON CONFLICT(name) DO UPDATE SET address=excluded.address,identity_number=excluded.identity_number",(name,address,identity)); self.conn.commit()
    def producers(self):
        return self.conn.execute("SELECT * FROM producers ORDER BY name").fetchall()
    def reasons(self,category):
        return [x["reason"] for x in self.conn.execute("SELECT reason FROM reasons WHERE category=? ORDER BY reason",(category,))]
    def add_reason(self,category,reason):
        if reason.strip(): self.conn.execute("INSERT OR IGNORE INTO reasons(category,reason) VALUES(?,?)",(category,reason.strip())); self.conn.commit()
    def save_invoice(self,d,invoice_id=None):
        now=datetime.now().isoformat(timespec="seconds")
        fields=(d["bon_number"],d.get("invoice_date",d.get("date","")),d["species"],d.get("producer",""),d.get("address",""),d.get("producer_id",""),d.get("agreer",""),d.get("quantity_qx"),d.get("collection_point",""),d.get("status","ACCEPTED"),d.get("reason",""),json.dumps(d.get("values",{}),ensure_ascii=False),json.dumps(d.get("layout",{}),ensure_ascii=False))
        if invoice_id:
            self.conn.execute("""UPDATE invoices SET bon_number=?,invoice_date=?,species=?,producer=?,address=?,producer_id=?,agreer=?,quantity_qx=?,collection_point=?,status=?,reason=?,data_json=?,layout_json=?,updated_at=? WHERE id=?""",fields+(now,invoice_id))
        else:
            self.conn.execute("""INSERT INTO invoices(bon_number,invoice_date,species,producer,address,producer_id,agreer,quantity_qx,collection_point,status,reason,data_json,layout_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",fields+(now,now))
        self.conn.commit()
        return self.conn.execute("SELECT id FROM invoices WHERE bon_number=?",(d["bon_number"],)).fetchone()["id"]
    def get_invoice(self,i):
        row=self.conn.execute("SELECT * FROM invoices WHERE id=?",(i,)).fetchone()
        if not row:return None
        d=dict(row); d["values"]=json.loads(d.pop("data_json") or "{}"); d["layout"]=json.loads(d.pop("layout_json") or "{}"); return d
    def history(self,term=""):
        q="%"+term.strip()+"%"
        return self.conn.execute("""SELECT id,bon_number,invoice_date,species,producer,status FROM invoices
        WHERE producer LIKE ? OR CAST(bon_number AS TEXT) LIKE ? OR invoice_date LIKE ?
        ORDER BY invoice_date DESC,id DESC""",(q,q,q)).fetchall()
    def delete_invoice(self,i): self.conn.execute("DELETE FROM invoices WHERE id=?",(i,)); self.conn.commit()
    def close(self): self.conn.close()
    def backup(self,target):
        target=Path(target); target.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(target,"w",zipfile.ZIP_DEFLATED) as z:
            self.conn.commit(); z.write(self.path,"bulletin.db")
            z.writestr("backup_info.json",json.dumps({"created":datetime.now().isoformat()},ensure_ascii=False))
