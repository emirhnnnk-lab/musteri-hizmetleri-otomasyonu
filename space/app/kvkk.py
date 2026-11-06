"""KVKK: kişisel veriyi LLM'e gitmeden önce maskeler. Sipariş numarası iş için gerekli olduğundan korunur."""
import re

DESENLER = [
    ("[TCKN]", re.compile(r"\b[1-9]\d{10}\b")),
    ("[KART]", re.compile(r"\b\d(?:[ -]?\d){14,15}\b")),
    ("[IBAN]", re.compile(r"\bTR\d{2}(?:\s?\d{4}){5}\s?\d{2}\b", re.I)),
    ("[EPOSTA]", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")),
    ("[TELEFON]", re.compile(r"(?:\+90|0)?\s?5\d{2}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}\b")),
]


def maskele(metin: str) -> tuple[str, list[str]]:
    """Maskelenmiş metni ve hangi veri türlerinin bulunduğunu döndürür."""
    bulunan = []
    for etiket, desen in DESENLER:
        if desen.search(metin):
            bulunan.append(etiket.strip("[]"))
            metin = desen.sub(etiket, metin)
    return metin, bulunan
