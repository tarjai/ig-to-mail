# ig-to-mail

iOS Shortcut ile paylaşılan Instagram linkini işler ve sonucu mail atar:

| Kısayol | Ne yapar |
|---|---|
| **IG Carousel → Mail** | Carousel görsellerini sırasıyla tek dikey JPEG'de birleştirir, her slaytı OCR'lar (Groq vision, hata olursa Tesseract), görsel + metni mailler |
| **IG Video → Mail** | Videonun sesini Groq Whisper ile yazıya döker, Türkçe değilse Türkçeye çevirir, çeviri + orijinali mailler |

Backend: **GitHub Actions** (ücretsiz, sunucu yok, uyku yok). Shortcut → GitHub API `repository_dispatch` → workflow → mail (~1-2 dk).
Hata olursa (cookie süresi dolması dahil) çözüm önerisini içeren hata maili gelir.

## Kurulum (tek seferlik)

### 1. Instagram cookie (yan hesap)
1. Yan hesapla masaüstü tarayıcıda `instagram.com`'a giriş yap.
2. DevTools → Application → Cookies → `https://www.instagram.com`.
3. `sessionid` değerini kopyala (opsiyonel: `csrftoken`, `ds_user_id`).

> Ana hesabı kullanma. Cookie genelde aylarca geçerli kalır; düşerse hata maili gelir, sadece secret'ı güncellersin.

### 2. Gmail app password
Google Hesabı → Güvenlik → 2 Adımlı Doğrulama açık olmalı → **Uygulama şifreleri** → yeni şifre oluştur (16 karakter).

### 3. Groq API key
https://console.groq.com/keys → Create API Key.

### 4. GitHub Secrets
Repo → Settings → Secrets and variables → Actions → **Secrets**:

| Secret | Değer |
|---|---|
| `GROQ_API_KEY` | Groq key |
| `IG_SESSIONID` | Instagram `sessionid` |
| `IG_CSRFTOKEN` | *(opsiyonel)* |
| `IG_DS_USER_ID` | *(opsiyonel)* |
| `GMAIL_USER` | `adresin@gmail.com` |
| `GMAIL_APP_PASSWORD` | 16 karakterlik uygulama şifresi |
| `MAIL_TO` | *(opsiyonel)* farklı alıcı; boşsa `GMAIL_USER` |

**Variables** (opsiyonel):

| Variable | Açıklama |
|---|---|
| `HEALTHCHECK_URL` | Herkese açık bir post linki. Her pazartesi bu post indirilmeye çalışılır; cookie düşmüşsa uyarı maili gelir |
| `GROQ_VISION_MODEL` | Varsayılan `qwen/qwen3.8-27b` |
| `GROQ_TEXT_MODEL` | Çeviri modeli, varsayılan `qwen/qwen3.8-27b` |
| `GROQ_WHISPER_MODEL` | Varsayılan `whisper-large-v3` |

Groq bir modeli kaldırırsa kod değiştirmeden buradan yenisini yazarsın.

### 5. GitHub token (Shortcut için)
GitHub → Settings → Developer settings → **Fine-grained tokens** → Generate:
- Repository access: **Only select repositories** → `ig-to-mail`
- Permissions → Repository → **Contents: Read and write**
- Expiration: en uzun süre (bittiğinde Shortcut 401 döner; yeni token oluşturup Shortcut'a yapıştır)

### 6. iOS Shortcut'lar
[`shortcuts/README.md`](shortcuts/README.md)

## Test
Actions → **process** → Run workflow → mode + url gir.

Lokal:
```bash
pip install -r requirements.txt pytest
pytest -q
DRY_RUN=1 GROQ_API_KEY=... IG_SESSIONID=... python -m igmail carousel "https://www.instagram.com/p/XXXX/"
# mail yerine work/mail-*.eml yazılır
```

## Limitler (ücretsiz katmanlar)
- **GitHub Actions**: private repoda 2000 dk/ay. Bir çalışma ~1-2 dk → ayda ~1000+ post.
- **Groq**: Whisper dosya başına 25MB (kod otomatik sıkıştırır/böler), saatlik ses süresi limiti var; 429'da SDK bekleyip tekrar dener.
- **Gmail SMTP**: günde 500 mail.
- **Scheduled health check**: GitHub, 60 gün commit olmayan repoda zamanlanmış workflow'u durdurur. Shortcut tetiklemeleri bundan etkilenmez.
