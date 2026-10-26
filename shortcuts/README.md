# iOS Shortcut kurulumu

İki kısayol aynı yapıda; sadece `event_type` farklı (`carousel` / `video`).
`<TOKEN>` = fine-grained token.

## IG Carousel → Mail

1. **Kısayollar** → `+` → adı: `IG Carousel → Mail`
2. Ayarlar (ⓘ) → **Paylaşma Sayfasında Göster** açık → Paylaşma Sayfası Türleri: **URL** ve **Metin**
3. Eylemler:

| # | Eylem | Ayar |
|---|---|---|
| 1 | **Girdiden URL'leri Al** | Girdi: *Kısayol Girdisi* |
| 2 | **Listeden Öğe Al** | *İlk Öğe* |
| 3 | **URL'nin İçeriklerini Al** | URL: `https://api.github.com/repos/tarjai/ig-to-mail/dispatches` |
| | | Yöntem: **POST** |
| | | Başlıklar: `Authorization` = `Bearer <TOKEN>` |
| | | `Accept` = `application/vnd.github+json` |
| | | İstek Gövdesi: **JSON** |
| | | `event_type` (Metin) = `carousel` |
| | | `client_payload` (Sözlük) → `url` (Metin) = *2. adımdaki Öğe* |
| 4 | **Bildirim Göster** | `İşleme alındı, mail 1-2 dk içinde gelir` |

## IG Video → Mail

Yukarıdakini çoğalt (uzun bas → **Çoğalt**), adını `IG Video → Mail` yap, `event_type` değerini `video` olarak değiştir.

## Kullanım
Instagram'da post → **Paylaş** (kağıt uçak) → **Paylaş…** / **Diğer** → `IG Carousel → Mail` veya `IG Video → Mail`.
Ya da linki kopyala → Kısayollar'dan çalıştır (Pano'dan almak için 1. adımın girdisini *Pano* yap).

## Sorun giderme
- **Bildirim geliyor ama mail gelmiyor**: GitHub → repo → Actions sekmesinde çalışmanın logu. Hata maili de gelmiş olmalı (Spam'e bak).
- **Shortcut hata veriyor / boş yanıt değil**: GitHub başarılı tetiklemede `204` ve boş gövde döner. `401` → token süresi dolmuş/yanlış. `404` → repo adı yanlış ya da token'ın bu repoya erişimi yok.
