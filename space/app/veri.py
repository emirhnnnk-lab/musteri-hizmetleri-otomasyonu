"""Örnek sipariş veritabanı ve SSS. Tamamen uydurma örnek veridir."""

SIPARISLER = {
    "SP-100231": {"durum": "kargoda", "kargo": "Örnek Kargo", "tahmini": "7 Kasım", "urun": "Deri bot"},
    "SP-100232": {"durum": "teslim_edildi", "kargo": "Örnek Kargo", "tahmini": "3 Kasım", "urun": "Yün kazak"},
    "SP-100233": {"durum": "hazirlaniyor", "kargo": None, "tahmini": "9 Kasım", "urun": "Spor ayakkabı"},
    "SP-100234": {"durum": "kargoda", "kargo": "Örnek Kargo", "tahmini": "6 Kasım", "urun": "Kot ceket"},
}

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
