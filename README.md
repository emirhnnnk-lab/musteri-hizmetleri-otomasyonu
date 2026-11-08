# Müşteri Hizmetleri Otomasyonu (n8n + LLM + İnsan Onayı)

> **EN summary:** Customer-service automation with n8n + a local LLM + human approval. Messages from WhatsApp/e-mail are PII-masked (KVKK/GDPR-style) before any model sees them, classified, and either answered automatically from templates with real order data or sent to an agent approval panel. Key design rule: the LLM never writes and sends free text on its own.

WhatsApp ve e-postadan gelen müşteri mesajlarını **n8n** ile alan, **LLM** ile sınıflandıran, güvenli olanları otomatik cevaplayan ve riskli olanları **temsilci onayına** düşüren bir otomasyon. Kişisel veriler LLM'e gitmeden **KVKK uyumlu şekilde maskelenir**.

**🔴 Canlı demo:** [huggingface.co/spaces/emrhnnnnnn/musteri-hizmetleri-demo](https://huggingface.co/spaces/emrhnnnnnn/musteri-hizmetleri-demo) — mesaj yazın, sistemin kararını görün (OpenAI `gpt-5.4-mini`; kod: [`space/`](space)).

![n8n iş akışı](docs/n8n-akis.jpg)

![Temsilci onay paneli](docs/panel.png)

## Ne yapıyor?

1. **n8n webhook** mesajı alır (WhatsApp/e-posta simülasyonu).
2. **KVKK maskeleme:** TC kimlik no, kart no, IBAN, telefon ve e-posta `[KART]`, `[TCKN]` gibi etiketlere çevrilir. Model, veritabanı ve panel kişisel veriyi hiç görmez.
3. **LLM analiz** (lokal `qwen2.5:3b`, Ollama): niyet, sipariş no, SSS konusu, duygu, güven.
4. **Doğrulama + kural katmanı** (Pydantic + anahtar kelime güvenlik ağı).
5. **Karar:**
   - Güvenli ise (kargo durumu, SSS) → **şablon + gerçek sipariş verisiyle** otomatik cevap.
   - Riskli ise (iade, ödeme, şikâyet, öfke, kişisel veri, düşük güven) → **temsilci paneline** düşer; temsilci taslağı düzenler, onaylar veya reddeder.

### Temel tasarım kararı
**LLM müşteriye serbest metin yazıp kendi başına gönderemez.** Model sadece sınıflandırır ve bilgi çıkarır. Otomatik giden her cevap şablondan ve veritabanındaki gerçek bilgiden üretilir. Böylece modelin uydurduğu bir kargo tarihi ya da verilmemiş bir iade sözü müşteriye gidemez.

## Değerlendirme

Ana ölçüt **kritik hata**: insan onayı gereken bir mesajın otomatik cevaplanması. Hedef 0.

| Sürüm | Niyet | Yönlendirme | **Kritik hata** |
|---|---|---|---|
| v1: ilk prompt | 4/24 | 16/24 | 0 |
| v2: prompt düzeltmesi, sadece LLM | 14/24 | 17/24 | **4** |
| v2: + doğrulama | 14/24 | 18/24 | **3** |
| **v3: + dayanak kontrolü ve güvenlik ağı** | **18/24** | **21/24** | **0** |
| v3, **ayrık test seti** (12 yeni mesaj, ayarlamada hiç kullanılmadı) | 8/12 | 11/12 | **0** |

Model: `qwen2.5:3b` (4 GB VRAM, GTX 1650), 24 mesaj yaklaşık 47 saniye. Sonuçlar: [`eval/`](eval).

### Süreçte ne öğrendim?
- **v1 (4/24):** Prompt'ta seçenekleri Python listesi gibi yazmıştım. Model de `"niyet": ["kargo_takip"]` diye liste döndürdü, şema doğrulaması reddetti ve her mesaj güvenli varsayılana ("diger") düştü. Sistem güvenliydi ama işe yaramıyordu. Çözüm: seçenekleri `a | b` biçiminde yazmak ve tek elemanlı listeyi açan bir doğrulayıcı.
- **v2 (kritik hata 3–4):** Model bazen alakasız mesajlara SSS konusu uydurdu. "Teşekkürler, ürün harika geldi!" mesajı beden tablosu cevabı aldı; "ayakkabıyı değiştirmek istiyorum" iade yerine SSS sanıldı. **Bu kabul edilemez**, çünkü riskli mesaj müşteriye otomatik cevapla gitti.
- **v3:** İki katman eklendi. (1) **Dayanak kontrolü:** SSS cevabı ancak mesaj gerçekten o konudan bahsediyorsa verilir. (2) **Anahtar kelime güvenlik ağı:** "iade, değiştir, iptal, para çekildi, kırık" gibi ifadeler niyeti sadece daha güvenli yöne çevirir. Kritik hata 0'a indi.
- **Aşırı uyum kontrolü:** Kuralları aynı 24 mesajda ayarladığım için skor şişmiş olabilirdi. Bu yüzden 12 yeni mesajlık ayrık bir set yazdım ve ona göre hiç ayar yapmadım. Orada da kritik hata 0, yönlendirme 11/12.
- **Uçtan uca testte bulunan iki hata:** (1) Windows'ta `curl` Türkçe karakterleri bozuk gönderdi, model bozuk metni anlayamadı. Çözüm: UTF-8 gönderen [`ornek_gonder.py`](ornek_gonder.py). (2) Model maskeli veriyi görüyordu ama **veritabanına ve panele orijinal kart numarası yazılıyordu**. Düzeltildi ve testi eklendi.

### Dürüst sınırlar
- Ayrık sette kural katmanı **niyet** doğruluğunu artırmadı (8/12, sadece LLM ile 9/12). Kuralların asıl katkısı doğruluk değil, **güvenlik**: riskli mesajın otomatik gitmesini engellemek.
- Sistem **temkinli**: bazı mesajlar otomatik cevaplanabilecekken insana gidiyor (yönlendirme hatalarının hepsi bu yönde). Bu, kasıtlı bir tercih.
- Küçük model `temperature=0` olsa bile aynı mesajda bazen farklı duygu ve güven veriyor.
- Gerçek WhatsApp/SMTP gönderimi yok; n8n'de "simülasyon" düğümü var. Gerçek kurulumda WhatsApp Business Cloud API veya SMTP düğümü buraya bağlanır.
- 36 mesajlık değerlendirme seti küçük; gerçek trafikte yeniden ölçülmeli.

## Kurulum

```bash
pip install -r requirements.txt
ollama pull qwen2.5:3b
python -m uvicorn app.main:app --port 8000      # servis + panel: http://localhost:8000/panel
```

**n8n:** Node 18/20/22 gerekir. `n8n/is-akisi.json` dosyasını n8n'e içe aktarıp aktif edin, sonra:

```bash
python ornek_gonder.py                           # 7 örnek mesajı webhook'a gönderir
```

**Bulut LLM ile (lokal GPU olmadan):** OpenAI uyumlu herhangi bir API (Groq, Gemini vb.)

```bash
LLM_PROVIDER=openai LLM_BASE_URL=... LLM_API_KEY=... LLM_MODEL=... python -m uvicorn app.main:app
```

**Test ve değerlendirme:**

```bash
python -m pytest -q                              # 16 test, LLM gerekmez
python -m eval.calistir                          # ana set
python -m eval.calistir --ayrik                  # ayrık set
python -m eval.calistir --sadece-llm             # kural katmanı kapalı karşılaştırma
```

## Teknolojiler
n8n · Python · FastAPI · Pydantic · Ollama (qwen2.5:3b) · OpenAI uyumlu API desteği · SQLite · pytest

Tüm sipariş, müşteri ve SSS verileri örnektir; gerçek bir şirkete ait değildir.
