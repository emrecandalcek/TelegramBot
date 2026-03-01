# 🎮 GameStudio Telegram Botu — Kurulum Rehberi

## 📁 Dosyalar
```
bot.py           ← Ana bot kodu
config.json      ← Tüm ayarlar ve içerik buraya
data.json        ← Otomatik oluşur (kullanıcı verileri)
requirements.txt ← Gerekli kütüphaneler
```

---

## ⚡ Hızlı Kurulum

### 1. Python Yükle
Python 3.10+ gerekli → https://python.org

### 2. Kütüphaneyi Yükle
```bash
pip install python-telegram-bot==20.7
```

### 3. Bot Token Al
- Telegram'da @BotFather'a mesaj at
- /newbot yaz ve bot ismi ver
- Verdiği token'ı kopyala

### 4. config.json Güncelle
```json
{
  "bot_token": "1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ",
  ...
}
```

### 5. Botu Gruba Ekle
- Botu gruba ekle
- Admin yetkisi ver (mesaj silme, ban, restrict için)

### 6. Önemli Ayar
Telegram'da gruba gidenlerIn bildirimini botun alabilmesi için:
- @BotFather → /setprivacy → botunu seç → DISABLE seç
Bu olmazsa bot yeni üyeleri göremez!

### 7. Botu Başlat
```bash
python bot.py
```

---

## 🎮 Özellikler

### 👋 Karşılama Sistemi
- Gruba katılan her yeni üyeyi selam verir
- 8 farklı rastgele karşılama mesajı
- Başlangıç XP ve altın verir
- İnline butonlarla menüye yönlendirir

### ⚡ XP & Seviye Sistemi
- Her mesaj → 3-8 XP (spam koruması: 3sn bekleme)
- Selam yazınca → +15 XP +10 Altın bonus
- 30 seviye, her seviyede artan XP gereksinimi
- Seviye atlanınca kutlama mesajı

### 🏅 Rank Sistemi (13 Rank)
```
Lv.1  → 🌱 Çaylak
Lv.3  → 📋 Stajyer
Lv.5  → 💻 Junior Dev
Lv.7  → ⚔️ Pixel Savaşçısı
Lv.9  → 🔬 Beta Tester
Lv.11 → 🛠️ Mid Dev
Lv.14 → 🧠 Senior Dev
Lv.17 → 🎨 Game Designer
Lv.20 → 👨‍💻 Lead Developer
Lv.23 → 🎬 Studio Director
Lv.26 → 🌟 Efsane Oyuncu
Lv.28 → 👑 Oyun Tanrısı
Lv.30 → 💀 Ölümsüz
```

### 🎁 Günlük Bonus + Streak
- /gunluk → Her gün 200 XP + 100 Altın
- Streak sistemi: Üst üste giriş = artan bonus
- 7 günlük streak → Haftalık süpriz bonus
- Streak kırılmazsa katlanarak artar

### 🏆 Liderlik Tablosu
- /liderlik → Sayfalı liderlik tablosu (10'ar kişi)
- XP'ye göre sıralı
- Rank ve seviye bilgisi gösterir

### 🧠 Trivia Sistemi
- /trivia → 12 farklı soru (Oyun/Teknik/Kültür)
- 30 saniye cevap süresi
- Doğru → +75 XP +40 Altın
- Yanlış → -10 XP ceza
- Herkes aynı soruya cevap verebilir

### 🎲 Mini Oyunlar
- /zar <miktar> → Zar at (4-6 gelirse 1.5x kazanırsın)
- /yatura <yazi/tura> <miktar> → 2x bahis

### 💰 Ekonomi
- /hediye <miktar> → Birine altın gönder
- Altın: Oyunlarda kullanılır, gönderilir, kazanılır

### 🏷 Unvan Sistemi
- /unvan → Seviyene göre özel unvan seç
- 12 farklı unvan
- Profilde görünür

### 🏅 Başarı Sistemi (15 Başarı)
Mesaj sayısı, seviye, streak, trivia, altın için
Her başarı → Ekstra XP ve Altın ödülü

### ⚠️ Moderasyon
- Yasaklı kelime → Otomatik silme + uyarı
- 3 uyarı → Otomatik 24 saat susturma
- Admin komutları: /ban /uyari /xpver

---

## 🔧 config.json Özelleştirme

### XP Oranlarını Değiştir
```json
"message_xp_min": 3,   ← Mesaj başı min XP
"message_xp_max": 8,   ← Mesaj başı max XP
"greet_bonus_xp": 15,  ← Selam bonusu
"daily_xp": 200        ← Günlük bonus XP
```

### Kötü Kelime Ekle
```json
"banned_words": ["kelime1", "kelime2"]
```

### Trivia Sorusu Ekle
```json
{
  "id": "qYENI",
  "category": "Kategori",
  "question": "Sorunuz?",
  "answer": "Doğru cevap",
  "wrong_answers": ["Yanlış1", "Yanlış2", "Yanlış3"]
}
```

### Yeni Rank Ekle
```json
{
  "name": "Rank Adı",
  "emoji": "🎯",
  "min_level": 15
}
```

---

## 📊 Komut Listesi

| Komut | Açıklama |
|-------|----------|
| /start | Botu başlat |
| /yardim | Komut listesi |
| /profil | Profilinizi görün |
| /liderlik | Liderlik tablosu |
| /gunluk | Günlük bonus al |
| /basarilar | Başarılarınız |
| /istatistik | Grup istatistikleri |
| /unvan | Unvan değiştir |
| /zar `<miktar>` | Zar oyunu |
| /yatura `<seçim> <miktar>` | Yazı-tura |
| /trivia | Bilgi sorusu |
| /hediye `<miktar>` | Altın gönder |
| /ban *(admin)* | Kullanıcı banla |
| /uyari *(admin)* | Kullanıcı uyar |
| /xpver *(admin)* | XP ver |

---

## ❓ Sık Sorulan Sorular

**Bot yeni üyeleri görmüyor?**
→ @BotFather'da privacy mode'u DISABLE yap

**Bot komutlara cevap vermiyor?**
→ Botu gruba admin olarak ekle

**Veriyi sıfırlamak istiyorum?**
→ data.json dosyasını sil

**Daha fazla soru eklemek istiyorum?**
→ config.json içindeki trivia_questions listesine ekle
