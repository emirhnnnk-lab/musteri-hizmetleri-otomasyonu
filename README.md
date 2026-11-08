# Müşteri Hizmetleri Otomasyonu (n8n + yapay zekâ + insan onayı)

> **EN summary:** Customer-service automation with n8n + a local LLM + human approval. Messages from WhatsApp/e-mail are PII-masked (KVKK/GDPR-style) before any model sees them, classified, and either answered automatically from templates with real order data or sent to an agent approval panel. Key design rule: the LLM never writes and sends free text on its own. Full English version: [README.en.md](README.en.md).

**Canlı demo:** [huggingface.co/spaces/emrhnnnnnn/musteri-hizmetleri-demo](https://huggingface.co/spaces/emrhnnnnnn/musteri-hizmetleri-demo). Bir mesaj yazın, sistemin ne karar verdiğini görün (OpenAI `gpt-5.4-mini`; kodu: [`space/`](space)).

Bir e-ticaret mağazasına WhatsApp'tan ve e-postadan gün boyu mesaj geliyor: "kargom nerede?", "beden tablosu var mı?", "iade etmek istiyorum", "param çekildi ama sipariş gelmedi". İlk ikisine otomatik cevap verilebilir. Son ikisine ise bir insanın bakması gerekiyor. Bu otomasyon mesajı alıyor, ne olduğunu anlıyor, güvenli olanları kendisi cevaplıyor, riskli olanları temsilcinin önüne koyuyor. Müşterinin kişisel verisi de yapay zekâya gitmeden **KVKK'ya uygun şekilde gizleniyor**.

![n8n iş akışı](docs/n8n-akis.jpg)

![Temsilci onay paneli](docs/panel.png)

## Nasıl çalışıyor
1. **Mesaj geliyor:** n8n mesajı alıyor (WhatsApp ve e-posta burada simüle ediliyor).
2. **Kişisel veri gizleniyor:** TC kimlik no, kart no, IBAN, telefon ve e-posta `[KART]`, `[TCKN]` gibi etiketlere çevriliyor. Model, veritabanı ve panel kişisel veriyi hiç görmüyor.
3. **Model mesajı okuyor** (yerel `qwen2.5:3b`): ne istendiğini, sipariş numarasını, hangi SSS konusu olduğunu, müşterinin ruh hâlini ve kendinden ne kadar emin olduğunu çıkarıyor.
4. **Kontrol ve kural katmanı:** modelin çıktısı belirli bir kalıba uyuyor mu diye kontrol ediliyor (Pydantic); üstüne bir anahtar kelime güvenlik ağı var.
5. **Karar:**
   - Güvenliyse (kargo durumu, SSS) → **hazır şablon + veritabanındaki gerçek sipariş bilgisiyle** otomatik cevap.
   - Riskliyse (iade, ödeme, şikâyet, öfke, kişisel veri, düşük güven) → **temsilci paneline** düşüyor. Temsilci taslağı düzeltip onaylıyor ya da reddediyor.

### En önemli tasarım kararım
**Model müşteriye kendi başına serbest metin yazıp gönderemiyor.** Sadece mesajı anlıyor ve bilgi çıkarıyor. Otomatik giden her cevap bir şablondan ve veritabanındaki gerçek bilgiden oluşuyor. Böylece modelin uydurduğu bir kargo tarihi ya da verilmemiş bir iade sözü müşteriye ulaşamıyor.

## Nasıl ölçtüm
Benim için ana ölçü **kritik hata**: insan onayı gereken bir mesajın otomatik cevaplanması. Hedef sıfır.

| Sürüm | Niyeti doğru anlama | Doğru yere yönlendirme | **Kritik hata** |
|---|---|---|---|
| v1: ilk prompt | 4/24 | 16/24 | 0 |
| v2: prompt düzeltildi, sadece model | 14/24 | 17/24 | **4** |
| v2: + çıktı kontrolü | 14/24 | 18/24 | **3** |
| **v3: + dayanak kontrolü ve güvenlik ağı** | **18/24** | **21/24** | **0** |
| v3, **ayrı test seti** (12 yeni mesaj, ayar yaparken hiç kullanılmadı) | 8/12 | 11/12 | **0** |

Model: `qwen2.5:3b` (4 GB'lık GTX 1650), 24 mesaj yaklaşık 47 saniye. Sonuçlar: [`eval/`](eval).

## Neler patladı, nasıl düzelttim
- **v1 (4/24):** Prompta seçenekleri Python listesi gibi yazmıştım. Model de cevabı `"niyet": ["kargo_takip"]` diye liste olarak döndürdü. Kontrol bunu reddetti ve her mesaj güvenli varsayılana ("diğer") düştü. Sistem güvenliydi ama hiçbir işe yaramıyordu. Çözüm: seçenekleri `a | b` biçiminde yazmak ve tek elemanlı listeyi açan bir kontrol eklemek.
- **v2 (kritik hata 3-4):** Model bazen alakasız mesajlara SSS konusu uydurdu. "Teşekkürler, ürün harika geldi!" mesajına beden tablosu gönderildi; "ayakkabıyı değiştirmek istiyorum" iade yerine SSS sanıldı. **Bu kabul edilemezdi**, çünkü riskli bir mesaj müşteriye otomatik cevapla gitmiş oluyordu.
- **v3:** İki katman ekledim. (1) **Dayanak kontrolü:** SSS cevabı ancak mesaj gerçekten o konudan bahsediyorsa veriliyor. (2) **Anahtar kelime güvenlik ağı:** "iade, değiştir, iptal, para çekildi, kırık" gibi ifadeler, niyeti sadece daha güvenli yöne çevirebiliyor. Kritik hata sıfıra indi.
- **Kendimi kandırıyor muyum kontrolü:** Kuralları aynı 24 mesaja bakarak ayarladığım için skor şişmiş olabilirdi. O yüzden 12 yeni mesajlık ayrı bir set yazdım ve ona göre hiç ayar yapmadım. Orada da kritik hata sıfır, yönlendirme 11/12.
- **Uçtan uca testte çıkan iki hata:** (1) Windows'ta `curl` Türkçe karakterleri bozuk gönderdi, model bozuk metni anlayamadı. Çözüm: UTF-8 gönderen [`ornek_gonder.py`](ornek_gonder.py). (2) Model gizlenmiş veriyi görüyordu, ama **veritabanına ve panele kartın gerçek numarası yazılıyordu**. Düzelttim ve testini ekledim.

### Dürüst sınırlar
- Ayrı test setinde kural katmanı niyeti anlama oranını artırmadı (8/12; sadece modelle 9/12). Kuralların asıl katkısı doğruluk değil **güvenlik**: riskli mesajın otomatik gitmesini engellemek.
- Sistem **temkinli**: otomatik cevaplanabilecek bazı mesajlar insana gidiyor (yönlendirme hatalarının hepsi bu yönde). Bu bilinçli bir tercih.
- Küçük model, sıcaklık 0 olsa bile aynı mesajda bazen farklı ruh hâli ve güven değeri veriyor.
- Gerçek WhatsApp ya da e-posta gönderimi yok; n8n'de bir "simülasyon" adımı var. Gerçek kurulumda buraya WhatsApp Business Cloud API ya da SMTP bağlanıyor.
- 36 mesajlık değerlendirme seti küçük; gerçek trafikte yeniden ölçülmesi gerekiyor.

## Kurulum
```bash
pip install -r requirements.txt
ollama pull qwen2.5:3b
python -m uvicorn app.main:app --port 8000      # servis + panel: http://localhost:8000/panel
```

**n8n:** Node 18/20/22 gerekiyor. `n8n/is-akisi.json` dosyasını n8n'e içe aktarıp etkinleştirin, sonra:

```bash
python ornek_gonder.py                           # 7 örnek mesajı webhook'a gönderir
```

**Bulut modeliyle (yerel ekran kartı olmadan):** OpenAI uyumlu herhangi bir API (Groq, Gemini vb.)

```bash
LLM_PROVIDER=openai LLM_BASE_URL=... LLM_API_KEY=... LLM_MODEL=... python -m uvicorn app.main:app
```

**Test ve değerlendirme:**

```bash
python -m pytest -q                              # 16 test, model gerekmez
python -m eval.calistir                          # ana set
python -m eval.calistir --ayrik                  # ayrı set
python -m eval.calistir --sadece-llm             # kural katmanı kapalı karşılaştırma
```

## Teknoloji
n8n · Python · FastAPI · Pydantic · Ollama (qwen2.5:3b) · OpenAI uyumlu API desteği · SQLite · pytest

Bütün sipariş, müşteri ve SSS verileri örnek; gerçek bir şirkete ait değil.

---
Geliştiren: **Emirhan Karaca**
