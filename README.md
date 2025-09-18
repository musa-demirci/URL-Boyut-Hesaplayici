# URL Boyut Hesaplayıcı

Bu uygulama, Excel (.xlsx) ve WordPress WXR (.xml) dosyalarındaki **URL**'lerin dosya boyutlarını hızlıca ölçer; URL başına *dosya adı, uzunluk, uzantı, boyut (MB) ve durum* bilgilerini çıkarır ve sonuçları **Excel (.xlsx)** olarak kaydeder.

> **Öne çıkanlar**
> - Harici bağımlılık **yok** (yalnızca Python standart kütüphanesi + tkinter)
> - Paralel isteklerle **hızlı** tarama
> - **İlerleme çubuğu**, yüzde, kalan süre ve bağlantı kopmalarına dayanıklı akış
> - Çıktıda **tıklanabilir** URL sütunu ve filtrelenebilir başlıklar
> - Windows için **DPI destekli** arayüz

![Logo](assets/logo.png)

---

## İçindekiler
- [Uygulama Ekran Görüntüsü](#uygulama-ekran-görüntüsü)
- [Desteklenen Dosya Türleri](#desteklenen-dosya-türleri)
- [Özellikler](#özellikler)
- [Kurulum (Windows)](#kurulum-windows)
- [Kullanım (Windows)](#kullanım-windows)
- [Çıktı Dosyası](#çıktı-dosyası)
- [Paketleme (PyInstaller, Windows)](#paketleme-pyinstaller-windows)
- [Klasör Yapısı](#klasör-yapısı)
- [SSS (Sıkça Sorulan Sorular)](#sss-sıkça-sorulan-sorular)
- [Teşekkürler](#teşekkürler)
- [Lisans](#lisans)

---

## Uygulama Ekran Görüntüsü



---

## Desteklenen Dosya Türleri

- **Excel (.xlsx)** — İlk sayfadaki başlık satırında verdiğiniz sütun adını bularak altındaki URL’leri okur.
- **WordPress WXR (.xml)** — `attachment_url` alanları ve içerikteki mutlak `href`/`src` URL’leri otomatik çıkarılır.

---

## Özellikler

- Dosyalardaki tüm URL’leri tespit edip **MB** cinsinden boyutlarını ölçer.
- Her URL için: **Dosya URL’si, Dosya adı, Uzunluk, Uzantı, Boyut (MB), Durum** sütunları.
- **Eşzamanlı** istekler ile yüzlerce URL’yi hızlı tarama.
- Canlı **ilerleme**, yüzde, **ETA** (tahmini kalan süre).
- Bağlantı koparsa **yeniden dene / iptal et** akışı.
- Çıktı Excel dosyasında **tıklanabilir URL** ve **filtreleme/sıralama**.
- Windows için **yüksek DPI** desteği.

---

## Kurulum (Windows)

1) **Python 3.8+ (Windows)** kurulu olduğundan emin olun.  
2) tkinter, Python ile birlikte gelir (Windows’da ayrıca kurulum gerektirmez).
3) Depoyu klonlayın:

   ```bash
   git clone https://github.com/<kullanıcı-adınız>/URL-Boyut-Hesaplayici.git
   cd URL-Boyut-Hesaplayici
   ```

> Harici bağımlılık yoktur; `pip install` gerekmez. Geliştirici paketlemesi için yalnızca **PyInstaller** kullanılır (bkz. aşağıda).

---

## Kullanım (Windows)

### 1) Çalıştırma
- **Windows**: `URL Boyut Hesaplayıcı.pyw` dosyasına çift tıklayın **veya**:

  ```
  python "URL Boyut Hesaplayıcı.pyw"
  ```

> Not: Dosya adı ASCII dışı karakter içeriyorsa terminalde tırnak içinde çalıştırın.

### 2) Arayüz Adımları
1. **Girdi dosyası (.xlsx / .xml)** seçin.
   - Excel için, ilk sayfadaki başlık satırında **URL sütun adı** (örn. `URL`) girin.
2. **Çıktı klasörü** seçin.
3. **Başlat**’a tıklayın.
4. İlerleme, yüzde ve **ETA**’yı takip edin. Gerekirse **İptal Et** ile sonlandırın.

### 3) WordPress WXR (.xml) İpuçları
- `attachment_url` alanları otomatik yakalanır.
- İçerik içindeki `href`/`src` mutlak URL’ler de taranır.
- Yalnızca `http`/`https` ile başlayan URL’ler dikkate alınır.

---

## Çıktı Dosyası

- Çıktı, seçtiğiniz klasöre **`<girdi-adı>_sonuc.xlsx`** olarak kaydedilir. Var olan dosyalar korunur (otomatik numaralandırma).
- Sütunlar:
  1. **Dosya URL’si** (tıklanabilir)
  2. **Dosya adı**
  3. **Uzunluk** (dosya adının uzunluğu)
  4. **Uzantı**
  5. **Boyut (MB)** — HEAD/Range kontrollerine göre tahmini boyut
  6. **Durum** — HTTP durum (`200` = OK, aksi halde kod veya `ERR`)

> Bazı sunucular `HEAD` yanıtında boyut vermez. Bu durumda 0-0 Range ile `GET` denenir; yine de toplam boyut bilinmeyebilir.

---

## Paketleme (PyInstaller, Windows)

**Windows (PowerShell/CMD):**
```
pip install pyinstaller
pyinstaller --noconsole --onefile --windowed ^
  --name "URL-Boyut-Hesaplayici" ^
  --icon assets/icon.ico ^
  --add-data "assets;assets" ^
  --add-data "docs;docs" ^
  "URL Boyut Hesaplayıcı.pyw"
```

> Çalıştırılabilir dosya `dist/` klasöründe oluşur.

---


## Klasör Yapısı

```
├─ assets/
│  ├─ icon.ico
│  └─ logo.png
├─ docs/
│  ├─ hakkinda.txt
│  ├─ lisans.txt
│  └─ tesekkurler.txt
├─ src/
│  ├─ gui.py
│  ├─ reader.py
│  ├─ writer.py
│  ├─ error_checking.py
│  └─ internet_connection.py
└─ URL Boyut Hesaplayıcı.pyw   # Uygulama giriş noktası (Windows)
```

---

## SSS (Sıkça Sorulan Sorular)

### Uygulama hangi işletim sistemlerini destekliyor?
Windows 10 ve 11’de test edilmiştir. 64-bit Python 3.8+ önerilir.

### Python kurulu olmak zorunda mı?
Geliştirme için evet (Python 3.8+). Son kullanıcılar için **PyInstaller** ile üretilen `.exe` dosyası kullanılabilir; Python gerekmez.

### SmartScreen uyarısı alıyorum, ne yapmalıyım?
İmzalanmamış uygulamalarda Windows Defender SmartScreen uyarı verebilir. Kaynağa güveniyorsanız **More info > Run anyway (Yine de çalıştır)** adımlarını izleyin.

### `tkinter` hatası alıyorum, çözümü nedir?
Windows’ta python.org’dan kurulan Python ile `tkinter` birlikte gelir. Eksikse Python’u yeniden yükleyin ve **tüm bileşenler**in kurulduğundan emin olun.

### Excel’de hangi sütunu okuyor?
İlk sayfadaki **başlık satırında** belirttiğiniz sütun adını kullanır (örn. `URL`). Başlık altındaki tüm hücrelerdeki URL’ler işlenir.

### WordPress WXR (.xml) dosyasında neleri tarıyor?
`attachment_url` alanlarını ve içerikteki mutlak `href`/`src` URL’lerini yakalar. Sadece `http`/`https` ile başlayan adresler dikkate alınır.

### Çıktı dosyası nereye kaydediliyor?
Seçtiğiniz klasöre `<girdi-adı>_sonuc.xlsx` olarak yazılır. Dosya mevcutsa üzerine yazmaz; otomatik numaralandırır.

### “Boyut (MB)” neden 0 ya da boş çıkıyor?
Bazı sunucular `Content-Length` döndürmez. Uygulama aralıklı (Range) denemesi yapar; yine de toplam boyut bilinmeyebilir. Bu durumda değer **0** ya da **bilinmiyor** olabilir.

### `Durum` sütununda `ERR` veya 4xx/5xx kodu görüyorum. Normal mi?
Evet. Bu, sunucunun hata döndürdüğü (404, 403, 500 vb.) ya da bağlantıda bir sorun olduğu anlamına gelir. Kimlik doğrulama isteyen (401/403) adresler desteklenmez.

### Tarama yavaş; hızlandırabilir miyim?
Uygulama eşzamanlı istekler kullanır ancak hız, **ağ koşulları** ve **hedef sunucu** kısıtlarına bağlıdır. Çok büyük listeleri parçalara bölüp ayrı çalıştırmanız önerilir.

### Zaman aşımı/bağlantı kopması oluyor. Ne önerirsiniz?
Ağ bağlantınızı kontrol edin; sorunlu URL’leri temizlemeye çalışın. Kurumsal proxy/filtreler taramayı engelleyebilir.

### Kurumsal proxy kullanıyorum; çalışır mı?
Kimlik doğrulamalı/özel proxy senaryoları desteklenmeyebilir. Böyle bir ortamda tarama sonuçları değişkenlik gösterebilir.

### Aynı URL birden fazla kez listemde var. Çıktıda tekrar eder mi?
Evet, girdiler ne ise çıktıda da yer alır. Tekrarları Excel’de **Veri > Yinelenenleri Kaldır** ile temizleyebilirsiniz.

### Çok büyük dosyalarla sorun yaşar mıyım?
Uygulama dosyanın **tamamını indirmez**, çoğunlukla başlık bilgisiyle çalışır. Ancak bazı sunucular bu bilgiyi sağlamadığından boyut saptanamayabilir.

### Türkçe karakter içeren yol/dosya adlarında sorun olur mu?
Genel olarak desteklenir. Komut satırından çalıştırırken dosya adını **tırnak içinde** verin:
```
python "URL Boyut Hesaplayıcı.pyw"
```

### Sonuç Excel dosyasında sütunları değiştirebilir miyim?
Üretilen dosyada filtreleme/sıralama serbesttir.

### `.exe` dosyası antivirüs tarafından işaretlenirse?
İmzalanmamış yeni derlemeler yanlış pozitif tetikleyebilir. Kaynağa güveniyorsanız istisna tanımlayabilir ya da `.exe`’yi **yerel olarak PyInstaller ile yeniden derleyip** deneyebilirsiniz.

---

## Lisans

+ [MIT](https://github.com/musa-demirci/URL-Boyut-Hesaplayici/tree/main?tab=MIT-1-ov-file) © 2025 Musa Demirci

---

## Teşekkürler

Bu uygulamanın hazırlanmasında yapay zekâ araçlarından yararlanılmıştır. Logo yapay zekâ ile üretilmiştir; uygulamanın tasarımı ve geliştirmesi tarafımdan gerçekleştirilmiştir.

