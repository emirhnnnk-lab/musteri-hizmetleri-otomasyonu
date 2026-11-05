"""Mesaj analizi ve karar.

Tasarım ilkesi: LLM sadece SINIFLANDIRIR ve BİLGİ ÇIKARIR. Müşteriye otomatik giden cevabı
şablon + gerçek veri üretir; model serbest metin yazıp müşteriye kendi başına gönderemez.
Riskli her durum (iade, ödeme, şikâyet, belirsizlik, kişisel veri) insan onayına düşer.
"""
import re
from typing import Literal, Optional

from pydantic import BaseModel, Field, ValidationError, field_validator

from . import kvkk, llm
from .veri import DURUM_METNI, SIPARISLER, SSS

NIYETLER = ["kargo_takip", "iade_talebi", "urun_sorusu", "odeme_sorunu", "sikayet", "diger"]
SSS_KONULARI = list(SSS) + ["yok"]
SIPARIS_DESENI = re.compile(r"\bSP[- ]?(\d{6})\b", re.I)
OFKE_KELIMELERI = ["rezalet", "berbat", "dolandırıcı", "avukat", "tüketici hakem", "şikayetvar", "şikâyetvar",
                   "son kez", "mahkeme", "skandal"]

# SSS cevabı ancak mesaj gerçekten o konudan bahsediyorsa verilir (dayanak kontrolü)
SSS_KELIMELERI = {
    "iade_suresi": ["iade", "kaç gün", "süre"],
    "kargo_ucreti": ["kargo ücret", "ücretsiz kargo", "kargo bedava", "kargo kaç"],
    "beden": ["beden", "tablo", "ölçü"],
    "kapida_odeme": ["kapıda"],
}
# Anahtar kelime güvenlik ağı: model kaçırsa bile riskli konu insana gider
RISK_KELIMELERI = {
    "iade_talebi": ["iade etmek", "iade et", "değiştir", "iptal"],
    "odeme_sorunu": ["para çekil", "iki kere", "çift çekim", "ödeme geçmedi", "hesabıma yatmadı", "parası", "yatmadı"],
    "sikayet": ["kırık", "yanlış", "bozuk", "sinirli", "rezalet", "berbat"],
}
KARGO_KELIMELERI = ["nerede", "gelmedi", "ne zaman gelir", "kargoya", "ulaşır", "durumu"]

SISTEM = f"""Bir e-ticaret mağazasının müşteri mesajını analiz et. SADECE şu JSON'u döndür:
{{"niyet": "{' | '.join(NIYETLER)}", "siparis_no": "SP-123456 biçiminde ya da null",
"sss_konusu": "{' | '.join(SSS_KONULARI)}", "duygu": "olumlu" | "notr" | "olumsuz", "guven": 0 ile 1 arası sayı,
"ozet": "tek cümle"}}
Niyetler: kargo_takip=siparişim nerede/ne zaman gelir; iade_talebi=ürünü iade/değişim yapmak istiyor;
urun_sorusu=ürün, beden, kargo ücreti, iade süresi, ödeme seçeneği gibi genel soru; odeme_sorunu=çift çekim, ödeme
geçmedi, para iadesi gelmedi; sikayet=kötü hizmet, kırık/yanlış ürün, kızgın; diger=hiçbiri.
sss_konusu sadece urun_sorusu için doldurulur: iade_suresi, kargo_ucreti, beden, kapida_odeme; uymuyorsa yok.
Her alana listeden TEK bir değer yaz, liste döndürme."""


class Analiz(BaseModel):
    niyet: Literal["kargo_takip", "iade_talebi", "urun_sorusu", "odeme_sorunu", "sikayet", "diger"] = "diger"
    siparis_no: Optional[str] = None
    sss_konusu: Literal["iade_suresi", "kargo_ucreti", "beden", "kapida_odeme", "yok"] = "yok"
    duygu: Literal["olumlu", "notr", "olumsuz"] = "notr"
    guven: float = Field(0.0, ge=0, le=1)
    ozet: str = ""

    @field_validator("niyet", "sss_konusu", "duygu", mode="before")
    @classmethod
    def tek_deger(cls, v, info):
        # küçük modeller bazen ["kargo_takip"] gibi tek elemanlı liste döndürür; boş liste = varsayılan
        if isinstance(v, list):
            if not v:
                return {"niyet": "diger", "sss_konusu": "yok", "duygu": "notr"}[info.field_name]
            return v[0] if len(v) == 1 else None  # birden çok değer: belirsiz, şema hatası → güvenli varsayılan
        return v

    @field_validator("siparis_no", mode="before")
    @classmethod
    def siparis_bicimi(cls, v):
        if not v:
            return None
        m = SIPARIS_DESENI.search(str(v))
        return f"SP-{m.group(1)}" if m else None


class Karar(BaseModel):
    aksiyon: Literal["otomatik_yanit", "insan_onayi"]
    gerekce: str
    yanit: str  # otomatikse gönderilecek metin, insan onayıysa taslak


def analiz_et(ham_metin: str) -> tuple[Analiz, list[str], list[str]]:
    """(analiz, maskelenen veri türleri, doğrulama notları)."""
    maskeli, pii = kvkk.maskele(ham_metin)
    notlar = []
    try:
        a = Analiz(**llm.json_sohbet(SISTEM, maskeli))
    except ValidationError as e:
        notlar.append(f"model çıktısı şemaya uymadı ({e.error_count()} hata), güvenli varsayılan kullanıldı")
        a = Analiz()
    # Kural katmanı: modelin kaçırdığını regex ve anahtar kelime ile düzelt
    m = SIPARIS_DESENI.search(ham_metin)
    gercek_no = f"SP-{m.group(1)}" if m else None
    if a.siparis_no != gercek_no:
        if a.siparis_no:
            notlar.append(f"model metinde olmayan sipariş no üretti ({a.siparis_no}), düzeltildi")
        a.siparis_no = gercek_no
    kucuk = ham_metin.lower()
    if any(k in kucuk for k in OFKE_KELIMELERI) and a.duygu != "olumsuz":
        notlar.append("öfke ifadesi bulundu, duygu 'olumsuz' yapıldı")
        a.duygu = "olumsuz"
    # Riskli anahtar kelime varsa niyet onunla değiştirilir (sadece daha güvenli yöne)
    for niyet, kelimeler in RISK_KELIMELERI.items():
        if any(k in kucuk for k in kelimeler) and a.niyet in ("urun_sorusu", "kargo_takip", "diger"):
            if not (niyet == "iade_talebi" and "kaç gün" in kucuk):
                notlar.append(f"'{niyet}' anahtar kelimesi bulundu, niyet {a.niyet} → {niyet}")
                a.niyet = niyet
                break
    if a.niyet == "diger" and any(k in kucuk for k in KARGO_KELIMELERI):
        notlar.append("kargo sorusu ifadesi bulundu, niyet diger → kargo_takip")
        a.niyet = "kargo_takip"
    if a.niyet == "urun_sorusu" and a.sss_konusu != "yok" and not any(k in kucuk for k in SSS_KELIMELERI[a.sss_konusu]):
        notlar.append(f"SSS konusu '{a.sss_konusu}' mesajda geçmiyor, otomatik cevap iptal")
        a.sss_konusu = "yok"
    if a.niyet == "urun_sorusu" and a.siparis_no:
        notlar.append("sipariş numaralı soru SSS ile cevaplanmaz")
        a.sss_konusu = "yok"
    if a.niyet != "urun_sorusu":
        a.sss_konusu = "yok"
    return a, pii, notlar


def karar_ver(a: Analiz, pii: list[str], esik: float = 0.6) -> Karar:
    if pii:
        return Karar(aksiyon="insan_onayi", gerekce=f"mesajda kişisel veri var ({', '.join(pii)})",
                     yanit="Merhaba, güvenliğiniz için lütfen kart, kimlik veya iletişim bilgilerinizi mesajla "
                           "paylaşmayın. Talebinizi bir temsilcimiz inceleyip size dönecek.")
    if a.duygu == "olumsuz" or a.niyet in ("sikayet", "iade_talebi", "odeme_sorunu", "diger"):
        return Karar(aksiyon="insan_onayi", gerekce=f"riskli konu: {a.niyet}, duygu: {a.duygu}",
                     yanit=_taslak(a))
    if a.guven < esik:
        return Karar(aksiyon="insan_onayi", gerekce=f"model emin değil (güven {a.guven:.2f})", yanit=_taslak(a))
    if a.niyet == "kargo_takip":
        if not a.siparis_no:
            return Karar(aksiyon="otomatik_yanit", gerekce="sipariş no eksik, istendi",
                         yanit="Merhaba, siparişinizi kontrol edebilmem için sipariş numaranızı (SP-123456 "
                               "biçiminde) paylaşır mısınız?")
        s = SIPARISLER.get(a.siparis_no)
        if not s:
            return Karar(aksiyon="insan_onayi", gerekce=f"{a.siparis_no} sistemde yok", yanit=_taslak(a))
        durum = DURUM_METNI[s["durum"]].format(**s)
        return Karar(aksiyon="otomatik_yanit", gerekce="sipariş bulundu, durum bildirildi",
                     yanit=f"Merhaba, {a.siparis_no} numaralı siparişiniz ({s['urun']}) {durum}. "
                           "Başka bir konuda yardımcı olabilir miyim?")
    if a.niyet == "urun_sorusu" and a.sss_konusu != "yok":
        return Karar(aksiyon="otomatik_yanit", gerekce=f"SSS cevabı: {a.sss_konusu}",
                     yanit=f"Merhaba, {SSS[a.sss_konusu]} Başka sorunuz olursa yazabilirsiniz.")
    return Karar(aksiyon="insan_onayi", gerekce="hazır cevabı olmayan soru", yanit=_taslak(a))


def _taslak(a: Analiz) -> str:
    """İnsan temsilci için düzenlenebilir taslak (müşteriye kendiliğinden gitmez)."""
    giris = "Merhaba, yaşadığınız sorun için üzgünüz. " if a.duygu == "olumsuz" else "Merhaba, "
    konu = {
        "iade_talebi": "iade talebinizi aldık; ürün ve sipariş bilgilerinizi kontrol edip iade sürecini başlatacağız.",
        "odeme_sorunu": "ödeme ile ilgili bildiriminizi aldık; ödeme kayıtlarınızı kontrol edip size döneceğiz.",
        "sikayet": "bildiriminizi aldık; konuyu inceleyip en kısa sürede size döneceğiz.",
    }.get(a.niyet, "mesajınızı aldık; bir temsilcimiz en kısa sürede size dönecek.")
    no = f" (Sipariş: {a.siparis_no})" if a.siparis_no else ""
    return giris + konu + no
