"""SQLite kayıt: gelen mesajlar, insan onay kuyruğu ve giden kutusu (gerçek gönderim yerine simülasyon)."""
import json
import os
import sqlite3
import time

DB = os.getenv("DB_YOLU", "mesajlar.db")


def _baglan():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute("""CREATE TABLE IF NOT EXISTS mesaj(
        id INTEGER PRIMARY KEY, kanal TEXT, gonderen TEXT, metin TEXT, analiz TEXT,
        aksiyon TEXT, gerekce TEXT, yanit TEXT, durum TEXT, zaman REAL, onaylayan TEXT)""")
    return c


def kaydet(kanal, gonderen, metin, analiz: dict, aksiyon, gerekce, yanit) -> int:
    durum = "gonderildi" if aksiyon == "otomatik_yanit" else "onay_bekliyor"
    with _baglan() as c:
        cur = c.execute("INSERT INTO mesaj(kanal,gonderen,metin,analiz,aksiyon,gerekce,yanit,durum,zaman)"
                        " VALUES(?,?,?,?,?,?,?,?,?)",
                        (kanal, gonderen, metin, json.dumps(analiz, ensure_ascii=False), aksiyon, gerekce,
                         yanit, durum, time.time()))
        return cur.lastrowid


def listele(durum=None):
    with _baglan() as c:
        q = "SELECT * FROM mesaj" + (" WHERE durum=?" if durum else "") + " ORDER BY id DESC"
        return [dict(r) for r in c.execute(q, (durum,) if durum else ())]


def karar_isle(mid: int, onay: bool, yanit: str | None, kim: str) -> dict | None:
    with _baglan() as c:
        r = c.execute("SELECT * FROM mesaj WHERE id=? AND durum='onay_bekliyor'", (mid,)).fetchone()
        if not r:
            return None
        yeni = "gonderildi" if onay else "reddedildi"
        c.execute("UPDATE mesaj SET durum=?, yanit=?, onaylayan=? WHERE id=?",
                  (yeni, yanit or r["yanit"], kim, mid))
        return dict(c.execute("SELECT * FROM mesaj WHERE id=?", (mid,)).fetchone())
