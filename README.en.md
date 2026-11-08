# Customer Service Automation (n8n + AI + human approval)

*Türkçe: [README.md](README.md)*

**Live demo:** [huggingface.co/spaces/emrhnnnnnn/musteri-hizmetleri-demo](https://huggingface.co/spaces/emrhnnnnnn/musteri-hizmetleri-demo). Type a message and see what the system decides (OpenAI `gpt-5.4-mini`; code: [`space/`](space)).

An online store gets messages all day on WhatsApp and e-mail: "where is my package?", "is there a size chart?", "I want to return this", "I was charged but the order never came". The first two can be answered automatically. The last two need a person. This automation receives the message, understands it, answers the safe ones itself and puts the risky ones in front of an agent. The customer's personal data is **masked before it reaches the AI**, in line with KVKK (Turkey's GDPR).

![n8n workflow](docs/n8n-akis.jpg)

![Agent approval panel](docs/panel.png)

## How it works
1. **A message arrives:** n8n receives it (WhatsApp and e-mail are simulated here).
2. **Personal data is masked:** national ID, card number, IBAN, phone and e-mail become tags like `[KART]`, `[TCKN]`. The model, the database and the panel never see personal data.
3. **The model reads the message** (local `qwen2.5:3b`): what is being asked, the order number, which FAQ topic, the customer's mood and how sure it is.
4. **Check and rule layer:** the model's output is checked against a fixed format (Pydantic), with a keyword safety net on top.
5. **Decision:**
   - If safe (shipping status, FAQ) → automatic reply built from **a template + the real order data in the database**.
   - If risky (refund, payment, complaint, anger, personal data, low confidence) → goes to the **agent panel**. The agent edits the draft and approves or rejects it.

### My most important design decision
**The model can never write free text and send it to a customer on its own.** It only understands the message and extracts information. Every automatic reply is built from a template and real data from the database. So a shipping date the model made up, or a refund promise nobody gave, can never reach a customer.

## How I measured it
My main measure is the **critical error**: a message that needed human approval getting an automatic reply. The target is zero.

| Version | Intent understood | Correct routing | **Critical errors** |
|---|---|---|---|
| v1: first prompt | 4/24 | 16/24 | 0 |
| v2: prompt fixed, model only | 14/24 | 17/24 | **4** |
| v2: + output check | 14/24 | 18/24 | **3** |
| **v3: + grounding check and safety net** | **18/24** | **21/24** | **0** |
| v3, **separate test set** (12 new messages, never used while tuning) | 8/12 | 11/12 | **0** |

Model: `qwen2.5:3b` (4 GB GTX 1650), 24 messages in about 47 seconds. Results: [`eval/`](eval).

## What broke, and how I fixed it
- **v1 (4/24):** I had written the options in the prompt like a Python list. So the model answered with a list too: `"niyet": ["kargo_takip"]`. The check rejected it and every message fell back to the safe default ("other"). The system was safe but useless. Fix: write the options as `a | b`, and add a check that unwraps a one-item list.
- **v2 (3-4 critical errors):** The model sometimes invented an FAQ topic for unrelated messages. "Thanks, the product arrived and it's great!" got a size chart; "I want to exchange the shoes" was taken as an FAQ instead of a return. **That was unacceptable**, because a risky message got an automatic reply.
- **v3:** I added two layers. (1) **Grounding check:** an FAQ answer is only given if the message really talks about that topic. (2) **Keyword safety net:** phrases like "return, exchange, cancel, money was taken, broken" can only push the intent in the safer direction. Critical errors went to zero.
- **Am I fooling myself? check:** I tuned the rules on the same 24 messages, so the score could be inflated. So I wrote a separate set of 12 new messages and never tuned anything on it. There too: zero critical errors, routing 11/12.
- **Two bugs found in end-to-end testing:** (1) On Windows, `curl` sent Turkish characters broken, and the model couldn't understand the broken text. Fix: [`ornek_gonder.py`](ornek_gonder.py), which sends UTF-8. (2) The model saw the masked data, but **the real card number was being written to the database and the panel**. I fixed it and added a test.

### Honest limits
- On the separate test set, the rule layer did not improve intent accuracy (8/12; model only: 9/12). The rules' real value is not accuracy but **safety**: stopping risky messages from being answered automatically.
- The system is **cautious**: some messages that could be answered automatically go to a human (all routing errors are in this direction). That is a deliberate choice.
- Even at temperature 0, the small model sometimes gives a different mood and confidence for the same message.
- There is no real WhatsApp or e-mail sending; n8n has a "simulation" step. In a real setup, WhatsApp Business Cloud API or SMTP connects there.
- The 36-message evaluation set is small; it needs to be measured again on real traffic.

## Setup
```bash
pip install -r requirements.txt
ollama pull qwen2.5:3b
python -m uvicorn app.main:app --port 8000      # service + panel: http://localhost:8000/panel
```

**n8n:** needs Node 18/20/22. Import `n8n/is-akisi.json` into n8n and activate it, then:

```bash
python ornek_gonder.py                           # sends 7 sample messages to the webhook
```

**With a cloud model (no local GPU):** any OpenAI-compatible API (Groq, Gemini, etc.)

```bash
LLM_PROVIDER=openai LLM_BASE_URL=... LLM_API_KEY=... LLM_MODEL=... python -m uvicorn app.main:app
```

**Tests and evaluation:**

```bash
python -m pytest -q                              # 16 tests, no model needed
python -m eval.calistir                          # main set
python -m eval.calistir --ayrik                  # separate set
python -m eval.calistir --sadece-llm             # comparison with the rule layer off
```

## Tech
n8n · Python · FastAPI · Pydantic · Ollama (qwen2.5:3b) · OpenAI-compatible API support · SQLite · pytest

All order, customer and FAQ data are samples and do not belong to a real company.

---
Built by **Emirhan Karaca**
