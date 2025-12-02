# 📝 Dinamik Sınav Takvimi Oluşturma Sistemi  
**KOÜ Bilgisayar Mühendisliği – Yazılım Lab. I / Proje 1**

Bu proje, üniversitelerde sınav programı hazırlama sürecini otomatikleştirmek için geliştirilmiş bir **masaüstü uygulamasıdır**.  
Derslik, ders ve öğrenci bilgilerinin Excel üzerinden içe aktarılmasıyla; çakışmasız, optimize edilmiş ve kapasite uygunluğunu gözeten bir sınav programı üretir. Ayrıca oturma planlarını görselleştirip PDF olarak dışa aktarır.

---

## 🚀 Özellikler

### 🔐 Kullanıcı Sistemi
- **Admin:** Tüm bölümlere erişim ve tüm yetkiler  
- **Bölüm Koordinatörü:** Yalnızca kendi bölümüne ait işlemleri yönetir  
- E-posta + şifre ile giriş  
- Varsayılan admin kullanıcısı veritabanında kayıtlı gelir  

---

## 🏫 Derslik Yönetimi
- Derslik ekleme, silme ve güncelleme  
- Kapasite, sıra–sütun sayısı, oturma yapısı (2’li / 3’lü) bilgileri  
- Arama: **Sınıf ID ile**  
- Derslik düzeninin grafiksel görselleştirilmesi  

---

## 📥 Excel Veri Aktarımı

### 🟦 Ders Listesi Yükleme
- Ders kodu, ders adı, öğretim üyesi, sınıf düzeyi, zorunlu/seçmeli bilgilerini okur  
- Tüm dersler otomatik olarak veritabanına kaydedilir  

### 🟩 Öğrenci Listesi Yükleme
- Öğrenci numarası, ad-soyad, sınıf düzeyi ve aldığı dersler içe aktarılır  
- Öğrenci–ders ilişkileri toplu olarak kayıt edilir  
- Hatalı satırlar için açıklayıcı uyarılar verilir  

---

## 👥 Öğrenci & Ders Listeleme

### 🔍 Öğrenci Listesi
- Öğrenci numarası ile arama  
- Öğrencinin adı ve aldığı derslerin listesi  

### 📚 Ders Listesi
- Tüm derslerin listesi  
- Bir derse tıklanınca o dersi alan tüm öğrenciler görüntülenir  

---

## 🗓️ Sınav Programı Oluşturma

### Kısıt Ayarları
- Programa dahil edilecek / hariç tutulacak dersler  
- Tarih aralığı seçme  
- Hafta içi/hafta sonu gün kısıtları  
- Sınav türü (Vize / Final / Bütünleme)  
- Varsayılan sınav süresi ve istisnalar  
- Bekleme süresi (default: 15 dk)

### Optimizasyon Kuralları
- Öğrencinin aynı saatte iki sınavı olamaz  
- Aynı sınıf düzeyine ait dersler farklı günlere dağılır  
- Kapasite yetersizse uyarı verilir  
- Derslik kullanımı minimumda tutulmaya çalışılır  
- Tüm çakışmalar detaylı hata mesajlarıyla bildirilir  

**Sonuç:** Çakışmasız bir sınav takvimi otomatik olarak oluşturulur.  
Takvim Excel olarak indirilebilir.

---

## 🪑 Oturma Planı Oluşturma
- Tüm sınavlar listelenir (ders, gün, saat, derslik)  
- Seçilen sınavın oturma düzeni grafiksel olarak gösterilir  
- Öğrenci → derslik → sıra/sütun eşleştirmesi yapılır  
- Oturma planı **PDF olarak export** edilir  
- Kapasite doluluğu veya “yan yana oturmama” gibi kurallar ihlal edilirse uyarı gösterilir  

---

## 🛠️ Kullanılan Teknolojiler

| Teknoloji | Amaç |
|----------|------|
| **Python** | Uygulamanın ana dili |
| **PySide6** | Masaüstü arayüzü |
| **SQLite** | Veritabanı |
| **pandas** | Excel parse işlemleri |
| **Modüler mimari** | Kod organizasyonu |

---

## 📦 Kurulum

```bash
git clone <repo-link>
cd <project-folder>

# Gereklilikleri yükleyin
pip install -r requirements.txt

# Uygulamayı başlatın
python main.py
