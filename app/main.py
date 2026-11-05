"""FastAPI servisi. n8n iş akışı /analiz'i çağırır; temsilci /panel'den onaylar."""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from . import depo, kvkk
from .analiz import analiz_et, karar_ver

app = FastAPI(title="Müşteri Hizmetleri Otomasyonu")


class Gelen(BaseModel):
    kanal: str = "whatsapp"
    gonderen: str = "anonim"
    metin: str


class OnayIstegi(BaseModel):
    onay: bool
    yanit: str | None = None
    temsilci: str = "temsilci"


@app.post("/analiz")
def analiz(g: Gelen):
    a, pii, notlar = analiz_et(g.metin)
    k = karar_ver(a, pii)
    # KVKK: veritabanına ve panele de sadece maskelenmiş metin yazılır
    maskeli, _ = kvkk.maskele(g.metin)
    mid = depo.kaydet(g.kanal, g.gonderen, maskeli, a.model_dump(), k.aksiyon, k.gerekce, k.yanit)
    return {"id": mid, "analiz": a.model_dump(), "kisisel_veri": pii, "dogrulama_notlari": notlar,
            **k.model_dump()}


@app.get("/kuyruk")
def kuyruk():
    return depo.listele("onay_bekliyor")


@app.get("/mesajlar")
def mesajlar():
    return depo.listele()


@app.post("/kuyruk/{mid}")
def karar(mid: int, o: OnayIstegi):
    r = depo.karar_isle(mid, o.onay, o.yanit, o.temsilci)
    if not r:
        raise HTTPException(404, "bekleyen mesaj yok")
    return r


@app.get("/panel", response_class=HTMLResponse)
def panel():
    return (Path(__file__).parent / "panel.html").read_text(encoding="utf-8")


@app.get("/saglik")
def saglik():
    return {"durum": "ok"}
