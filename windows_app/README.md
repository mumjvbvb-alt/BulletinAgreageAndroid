# Bulletin d’Agréage — Windows

نسخة Windows مستقلة من تطبيق Bulletin d’Agréage.

تشمل الإدخال والحساب والتحكم في حجم الخط والملصقات وتصدير PDF.

## التشغيل من المصدر
```powershell
py -m pip install -r requirements.txt
py main.py
```

## إنشاء EXE
```powershell
pyinstaller --noconfirm --clean --onefile --windowed --name BulletinAgreage main.py
```
الملف الناتج يكون في `dist/BulletinAgreage.exe`.
