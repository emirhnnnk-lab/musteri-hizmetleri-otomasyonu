"""Değerlendirme: niyet doğruluğu, yönlendirme doğruluğu ve EN ÖNEMLİSİ güvenlik
(insan onayı gereken mesajın otomatik cevaplanması = kritik hata, hedef 0).

Kullanım: python -m eval.calistir [--sadece-llm] [--ayrik]
--sadece-llm: kural katmanı kapalı (modelin çıplak hali) karşılaştırma için.
"""
import json
import sys
import time
from pathlib import Path

from app import analiz as A
from app import kvkk, llm

sadece_llm = "--sadece-llm" in sys.argv
ayrik = "--ayrik" in sys.argv  # ayarlamada hiç kullanılmamış ayrı test seti
satirlar = [json.loads(s) for s in Path(__file__).with_name("ayrik.jsonl" if ayrik else "veri.jsonl").read_text(encoding="utf-8").splitlines() if s]
niyet_ok = yon_ok = kritik = 0
hatalar = []
t0 = time.time()
for s in satirlar:
    if sadece_llm:
        try:
            a = A.Analiz(**llm.json_sohbet(A.SISTEM, s["metin"]))
        except Exception:
            a = A.Analiz()
        pii = []
    else:
        a, pii, _ = A.analiz_et(s["metin"])
    k = A.karar_ver(a, pii)
    niyet_ok += a.niyet == s["niyet"]
    yon_ok += k.aksiyon == s["aksiyon"]
    if s["aksiyon"] == "insan_onayi" and k.aksiyon == "otomatik_yanit":
        kritik += 1
    if a.niyet != s["niyet"] or k.aksiyon != s["aksiyon"]:
        hatalar.append({"metin": s["metin"], "beklenen": [s["niyet"], s["aksiyon"]],
                        "gelen": [a.niyet, k.aksiyon], "gerekce": k.gerekce})
n = len(satirlar)
sonuc = {"mod": ("sadece_llm" if sadece_llm else "llm+kurallar") + ("_ayrik" if ayrik else ""), "model": llm.MODEL, "ornek": n,
         "niyet_dogrulugu": f"{niyet_ok}/{n}", "yonlendirme_dogrulugu": f"{yon_ok}/{n}",
         "kritik_hata_riskli_mesaj_otomatik_gitti": kritik, "sure_sn": round(time.time() - t0, 1), "hatalar": hatalar}
Path(__file__).with_name(f"sonuc_{sonuc['mod']}.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=2), encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")
print(json.dumps(sonuc, ensure_ascii=False, indent=2))
