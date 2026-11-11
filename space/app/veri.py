"""Örnek sipariş veritabanı ve SSS. Tamamen uydurma örnek veridir."""
from datetime import date, timedelta

_AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


def _tarih(gun_farki: int) -> str:
    """Bugüne göre tarih ("13 Kasım" gibi); örnek veri hiç eskimesin diye her okumada hesaplanır."""
    d = date.today() + timedelta(days=gun_farki)
    return f"{d.day} {_AYLAR[d.month - 1]}"


_SIPARISLER = {
    "SP-100231": {"durum": "kargoda", "kargo": "Örnek Kargo", "gun": 2, "urun": "Deri bot"},
    "SP-100232": {"durum": "teslim_edildi", "kargo": "Örnek Kargo", "gun": -3, "urun": "Yün kazak"},
    "SP-100233": {"durum": "hazirlaniyor", "kargo": None, "gun": 3, "urun": "Spor ayakkabı"},
    "SP-100234": {"durum": "kargoda", "kargo": "Örnek Kargo", "gun": 1, "urun": "Kot ceket"},
}


class _Siparisler(dict):
    """.get() / [] çağrısında "tahmini" alanını bugüne göre üretir."""

    def __getitem__(self, anahtar):
        s = dict(super().__getitem__(anahtar))
        s["tahmini"] = _tarih(s.pop("gun"))
        return s

    def get(self, anahtar, varsayilan=None):
        return self[anahtar] if anahtar in self else varsayilan


SIPARISLER = _Siparisler(_SIPARISLER)

DURUM_METNI = {
    "kargoda": "kargoya verildi, tahmini teslim {tahmini}",
    "teslim_edildi": "{tahmini} tarihinde teslim edildi olarak görünüyor",
    "hazirlaniyor": "hazırlanıyor, tahmini kargoya veriliş {tahmini}",
}

SSS = {
    "iade_suresi": "Ürünleri teslimattan itibaren 14 gün içinde ücretsiz iade edebilirsiniz.",
    "kargo_ucreti": "500 TL ve üzeri siparişlerde kargo ücretsizdir, altında 49,90 TL'dir.",
    "beden": "Beden tablosu her ürün sayfasında 'Beden Rehberi' bağlantısında yer alır.",
    "kapida_odeme": "Kapıda ödeme seçeneği 2.000 TL'ye kadar olan siparişlerde kullanılabilir.",
}
