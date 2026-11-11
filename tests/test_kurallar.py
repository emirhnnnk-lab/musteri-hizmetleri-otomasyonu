"""LLM'siz birim testler: model taklit edilir, kural ve güvenlik katmanı doğrulanır."""
import pytest
from fastapi.testclient import TestClient

from app import analiz as A
from app import kvkk
from app.veri import SIPARISLER


@pytest.fixture
def model(monkeypatch):
    def ayarla(cikti):
        monkeypatch.setattr(A.llm, "json_sohbet", lambda s, k: cikti)
    return ayarla


def test_maskeleme():
    m, t = kvkk.maskele("Tel 0532 123 45 67, TC 12345678901, kart 4543 1234 5678 9012, a@b.com SP-100231")
    assert "0532" not in m and "12345678901" not in m and "4543" not in m and "a@b.com" not in m
    assert "SP-100231" in m
    assert set(t) == {"TELEFON", "TCKN", "KART", "EPOSTA"}


def test_kargo_otomatik(model):
    model({"niyet": "kargo_takip", "siparis_no": "SP-100231", "duygu": "notr", "guven": 0.9})
    a, pii, _ = A.analiz_et("SP-100231 nerede?")
    k = A.karar_ver(a, pii)
    assert k.aksiyon == "otomatik_yanit" and SIPARISLER["SP-100231"]["tahmini"] in k.yanit


def test_uydurma_siparis_no_duzeltilir(model):
    model({"niyet": "kargo_takip", "siparis_no": "SP-100231", "guven": 0.9})
    a, pii, notlar = A.analiz_et("siparişim nerede")
    assert a.siparis_no is None and notlar
    assert "sipariş numaranızı" in A.karar_ver(a, pii).yanit


def test_ofke_insana_gider(model):
    model({"niyet": "kargo_takip", "siparis_no": "SP-100231", "duygu": "notr", "guven": 0.95})
    a, pii, _ = A.analiz_et("SP-100231 nerede rezalet")
    assert A.karar_ver(a, pii).aksiyon == "insan_onayi"


def test_kisisel_veri_insana_gider(model):
    model({"niyet": "kargo_takip", "guven": 0.99})
    a, pii, _ = A.analiz_et("numaram 05321234567 siparişim nerede")
    assert A.karar_ver(a, pii).aksiyon == "insan_onayi"


def test_bozuk_cikti_guvenli(model):
    model({"niyet": "para_ver", "guven": 7})
    a, pii, notlar = A.analiz_et("bana para iade et")
    assert a.niyet in ("diger", "iade_talebi") and notlar
    assert A.karar_ver(a, pii).aksiyon == "insan_onayi"


def test_dusuk_guven(model):
    model({"niyet": "urun_sorusu", "sss_konusu": "kargo_ucreti", "guven": 0.3})
    a, pii, _ = A.analiz_et("kargo ne kadar")
    assert A.karar_ver(a, pii).aksiyon == "insan_onayi"


@pytest.mark.parametrize("niyet", ["iade_talebi", "odeme_sorunu", "sikayet", "diger"])
def test_riskli_niyet_asla_otomatik_degil(model, niyet):
    model({"niyet": niyet, "duygu": "olumlu", "guven": 1.0})
    a, pii, _ = A.analiz_et("mesaj")
    assert A.karar_ver(a, pii).aksiyon == "insan_onayi"


def test_api_onay_akisi(model, tmp_path, monkeypatch):
    monkeypatch.setattr("app.depo.DB", str(tmp_path / "t.db"))
    from app.main import app
    c = TestClient(app)
    model({"niyet": "iade_talebi", "siparis_no": "SP-100232", "guven": 0.9})
    r = c.post("/analiz", json={"metin": "SP-100232 iade etmek istiyorum"}).json()
    assert r["aksiyon"] == "insan_onayi"
    assert len(c.get("/kuyruk").json()) == 1
    s = c.post(f"/kuyruk/{r['id']}", json={"onay": True, "yanit": "İadeniz başlatıldı."}).json()
    assert s["durum"] == "gonderildi" and s["yanit"] == "İadeniz başlatıldı."
    assert c.get("/kuyruk").json() == []
    assert c.post(f"/kuyruk/{r['id']}", json={"onay": True}).status_code == 404


def test_tek_elemanli_liste_acilir(model):
    model({"niyet": ["kargo_takip"], "sss_konusu": [], "siparis_no": "SP-100231", "guven": 0.9})
    a, pii, notlar = A.analiz_et("SP-100231 nerede?")
    assert a.niyet == "kargo_takip" and not notlar


def test_sss_dayanaksizsa_otomatik_gitmez(model):
    model({"niyet": "urun_sorusu", "sss_konusu": "beden", "guven": 0.95})
    a, pii, notlar = A.analiz_et("Teşekkürler, ürün harika geldi!")
    assert A.karar_ver(a, pii).aksiyon == "insan_onayi" and notlar


def test_degisim_kelimesi_insana(model):
    model({"niyet": "urun_sorusu", "sss_konusu": "beden", "guven": 0.95})
    a, pii, _ = A.analiz_et("Ayakkabıyı bir büyük numarayla değiştirmek istiyorum")
    assert a.niyet == "iade_talebi" and A.karar_ver(a, pii).aksiyon == "insan_onayi"


def test_veritabanina_kisisel_veri_yazilmaz(model, tmp_path, monkeypatch):
    monkeypatch.setattr("app.depo.DB", str(tmp_path / "t.db"))
    from app.main import app
    c = TestClient(app)
    model({"niyet": "odeme_sorunu", "guven": 0.9})
    c.post("/analiz", json={"metin": "Kartım 4543 1234 5678 9012 ile ödeme geçmedi, tel 0532 123 45 67"})
    kayit = c.get("/mesajlar").json()[0]["metin"]
    assert "4543" not in kayit and "0532" not in kayit and "[KART]" in kayit
