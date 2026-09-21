import sys, os, math, datetime, base64
from PySide6.QtCore import Qt, QRectF, QPoint
from PySide6.QtGui import QPainter, QPen, QFont, QColor, QPixmap
from PySide6.QtWidgets import (
    QApplication, QWidget, QLineEdit, QPushButton, QLabel, QComboBox,
    QVBoxLayout, QHBoxLayout, QScrollArea, QMessageBox, QFrame,
    QSpinBox, QGroupBox, QToolButton, QInputDialog
)
from PySide6.QtPrintSupport import QPrinter

# Exact reference proportions: 1338 x 2048.
DW, DH = 1338.0, 2048.0

# Clean crop of the wheat/ring logo from the supplied reference form.
LOGO_B64 = """iVBORw0KGgoAAAANSUhEUgAAAFAAAABQCAYAAACOEfKtAAAFU0lEQVR42u1cy04UQRQ9DMyggw8QExcGXZmAbjXGpSvjhi/gC/gC/sCVS76AL3DniqUbtkaIK0UXLFATAwID0i64hZWbej96qpuupFIzQ0911+nbt+459w5A+9skjb8BzKJrXaurDWjcA7BEryea/Ai9BlABeEvvpzOdT8y7Sec7oXG+yeC9pEX8pvFNBhDFXBt0jlMaz9oE4DGN8usVOmYqAXjrNOeIjQtNfYRNAFYAjmhcZsfbmgB7RTNvdVUAlLvwVYuWxYo5l9lNGAuAvcJ2zVMA27TgKnLBIwB92oG/0VxVmy2wMjh9AeQis1ZdF+d5WqChBIPo8siJfk7jMABAAd5LT79afOvTuOphjeeS9Swwv6bqfFO6RuNX+vx6W9jBmiOIrgCKeVbp2Bs0bjG3MGyDJYqY7Y2jP/sF4CYDgu/ccmDeGiYiLOeptOANBqJ4xN5pANL1U4/5GslEVE5fPHrrGhonHu9ttpGoduhNhcWpLLrRgTS3wGM2rjHg5I1mVwHiXxq3JPBsPrWVANq4sAg79hVhzTb9bXgVqJwNQFPcJhZ6KB23K82dkho2HkDdgmUA96XPQufLAuBUQYALf/aRrPAugBl2Q84d5zohH/kMwI7ndxvPhVVUbt4jzGkdlQvhwjKQAHDHEcBQfbH45iqAxgDId/Wh5BIqAHNNDKSfA/jC+KmvmOACoI0LN5aJPKKLf0/vbwaICSYAORe+1VYqV9GiZL6amgu3KiunE0BV6ok8bjHa5sKF5bE1WTmbgsx9Vt9BTOBc2MWntp7KqcIOFy7sGhZdCS7sQ+UGpXHhktOa8q4tFj+iG7Ip0bUiAtxSm8gNyz51i4Cc7riwW15YgOeSlevywpFiQseFIwDUceE9AI/p9R+2KRULcCouPCJNUJdkUuVYxMazKR0zh4v6GFNcOV0CYCLs+EHvlxgXtmXRfLoqy8ep4ZEBQBOzqa3psmg/6fMn9P6QcdfbGurl2jkX1t2QkQVAW545e9ymo14cQFNemFcSnDns0L55YRuAFex566TNRv51SSCdmGC7IZzKDdioksfEuZ7QMT8drduUt45uLvKTWOx3OvYF/NKa3CWI+XbZNdjColAAc9Rwa+WiKgGAqsCXiwkxXPgegE+WnTxbXOlbjhYKoIn8z+Li5xEIFCdiAIzK8oUURHIQP9Mcr2qkcuIcr+h7nyPAC6aGoVm0WP0uNZW7pgmzQrqzPBaTxzVF+iE3JCatOQVztVdM8H4p0OZSKSoy8x2SlMZVWntK40OymKMS5SeXR3iA8CJzmwX6xG0TCaxQm+XzleBN3aZ2uIZFNjHBFJjr2jDycVYC6PtDFlM/dMxB6PK4rgtQ5Zldm0+xUq0Angcmb2LzwiHKkY/CbYwSkk+YQd3RceFY+S3UYC7X25PMcZfufN/zYv7SBd0lxTd215wE8IA0xcbkcZP7hMQCrSwm9BOdI8mm2WuIxfygc0xKsV0xLXRbryPz3wdwkGn+IiywDiZxQ2I3xbXSAcxpgckAPCz5Aktv3SMcLpYAwEyvs6F2W2CuJlQZ12qvDsCcFjhTcpiQyfqEqrxNfnYwjkc49T/K6XxgQ1oW8aQ0MaFE6mpcbwyAKfXAunbf4rJywvcdFOoHU1yf8p+Z9ehFKrlookDuOon/ia5hzrsTI+n7ZuXqFCOA+MS6trSjJ4Uf38g8+wTiuHa5FE2wig90PffreCpS5oXHVYMc+vPZZNVZqSoT6qxBTlW0nqzAMlVxkcvFrTJf5dpiq8dyX1/2Cyy5J6uRjimwbGoPqbWxCgaAX4lvU3u2nznkctKl9KhipX+c9NIXEktZLAAAAABJRU5ErkJggg=="""

FIELDS = [
    ("date", 805, 278, 225, 34, False),
    ("producteur", 260, 383, 275, 32, False),
    ("adresse", 210, 418, 325, 32, False),
    ("pointCollecte", 315, 453, 220, 32, False),
    ("agreur", 790, 383, 265, 32, False),
    ("quantite", 775, 418, 240, 32, False),
    ("numeroBon", 820, 453, 235, 32, False),
    ("carteIdentite", 105, 1870, 370, 38, False),
    ("poids", 655, 642, 105, 28, True),
    ("humidite", 655, 674, 105, 32, True),
    ("ergot", 655, 714, 105, 35, True),
    ("tamis", 655, 758, 105, 65, True),
    ("debris", 655, 833, 99, 99, True),
    ("grainesNuisibles", 655, 941, 105, 60, True),
    ("impur1Total", 655, 1009, 105, 34, True),
    ("casses", 655, 1050, 105, 31, True),
    ("boutes", 655, 1088, 105, 43, True),
    ("roux", 655, 1139, 105, 41, True),
    ("mouchetes", 655, 1239, 105, 31, True),
    ("punaises", 655, 1279, 105, 33, True),
    ("piques", 655, 1322, 105, 41, True),
    ("impur2Total", 655, 1372, 105, 32, True),
    ("mitadin", 655, 1422, 105, 44, True),
    ("bleTendre", 655, 1475, 105, 36, True),
    ("mitadinTotal", 655, 1520, 105, 52, True),
]

def num(s):
    try:
        return float((s or "").replace(",", ".").strip())
    except Exception:
        return None

def tranches(exces, taille):
    return 0 if exces <= 0 else math.ceil(exces / taille)

def calculate(v):
    p,h,e = num(v("poids")), num(v("humidite")), num(v("ergot"))
    t,d,gn = [num(v(k)) or 0 for k in ("tamis","debris","grainesNuisibles")]
    c,b,r,m,pu,pi = [num(v(k)) or 0 for k in ("casses","boutes","roux","mouchetes","punaises","piques")]
    imp1, imp2 = t+d+gn, c+b+r+m+pu+pi
    mit, tender = num(v("mitadin")) or 0, num(v("bleTendre")) or 0
    mit_total = mit + tender
    bonus = refa = 0.0
    rows, notes = {}, []
    def add(k, bb=0.0, rr=0.0):
        nonlocal bonus, refa
        if bb or rr: rows[k] = (bb, rr)
        bonus += bb; refa += rr
    if p is not None:
        if p > 80:
            add("poids", tranches(min(p,82)-80,.25)*.15 + tranches(min(p,83)-82,.25)*.10 +
                (tranches(min(p,84)-83,.25)+tranches(max(p-84,0),.25))*.05)
        elif 72 <= p < 76:
            add("poids", rr=tranches(76-max(p,75),.25)*.10 + tranches(75-max(p,74),.25)*.20 + tranches(74-p,.25)*.30)
        elif p < 72:
            notes.append("Poids spécifique inférieur à 72 kg/hl : hors critère sain, loyal et marchand.")
    if h is not None and h > 17: notes.append("Humidité supérieure à 17 % : hors limite.")
    if e is not None and e > 1: notes.append("Ergot supérieur à 1 ‰ : hors limite.")
    if imp1 < 1: add("impur1", bb=tranches(1-imp1,.25)*.125)
    elif 3 < imp1 <= 6: add("impur1", rr=tranches(imp1-3,.25)*.125)
    elif imp1 > 6: notes.append("Impuretés 1ère catégorie > 6 % : prix à débattre.")
    if c > 5: add("casses", rr=tranches(c-5,.25)*.075)
    if b > 5: add("boutes", rr=tranches(b-5,1)*.05)
    if 10 < imp2 <= 20: add("impur2", rr=tranches(imp2-10,1)*.50)
    elif imp2 > 20: notes.append("Impuretés 2ème catégorie > 20 % : hors barème.")
    if 0 <= mit_total <= 10: add("mitadin", bb=.25)
    elif 20 < mit_total <= 70: add("mitadin", rr=tranches(mit_total-20,1)*.05)
    elif mit_total > 70: notes.append("Mitadin > 70 % : paiement au prix du blé tendre avec son barème.")
    if tender > 10: notes.append("Blé tendre > 10 % : paiement du blé dur au prix du blé tendre avec son barème.")
    return bonus, refa, imp1, imp2, mit_total, rows, notes

class Sticker(QFrame):
    def __init__(self, text, refusal=False, parent=None):
        super().__init__(parent)
        self.refusal = refusal
        self.drag = None
        self.resize_start = None
        self.setObjectName("refusalSticker" if refusal else "priceSticker")
        self.edit = QLineEdit(text, self)
        self.edit.setAlignment(Qt.AlignCenter)
        self.edit.setStyleSheet("QLineEdit{border:0;background:transparent;padding:6px;font-weight:700;}")
        self.edit.setReadOnly(False)
        self.edit.setToolTip("انقر مرتين أو استعمل زر تعديل الملصق لتغيير النص")
        self.handle = QLabel("↘", self)
        self.moveh = QLabel("✥", self)
        self.edit.mouseDoubleClickEvent = self._double_edit
        for w in (self.handle, self.moveh): w.setAlignment(Qt.AlignCenter)
        self.handle.setStyleSheet("background:rgba(0,0,0,18);font-size:18px;border:0;")
        self.moveh.setStyleSheet("background:rgba(0,0,0,12);font-size:16px;border:0;")
        self.resize(360,100)
        self.moveh.mousePressEvent=self._move_press; self.moveh.mouseMoveEvent=self._move_move
        self.handle.mousePressEvent=self._resize_press; self.handle.mouseMoveEvent=self._resize_move
    def _double_edit(self, e):
        self.edit_text_dialog()
    def edit_text_dialog(self):
        text, ok = QInputDialog.getMultiLineText(self, "تعديل الملصق",
            "النص الذي سيظهر داخل الملصق:", self.edit.text())
        if ok:
            self.edit.setText(text)
            self.adjust_text()
    def adjust_text(self):
        self.edit.setToolTip("النص الحالي: " + self.edit.text())
    def resizeEvent(self,e):
        self.edit.setGeometry(8,6,max(1,self.width()-58),max(1,self.height()-12))
        self.moveh.setGeometry(self.width()-50,0,50,40)
        self.handle.setGeometry(self.width()-54,self.height()-54,54,54)
    def _move_press(self,e): self.drag=(e.globalPosition().toPoint(),self.pos())
    def _move_move(self,e):
        if self.drag:
            p0,p1=self.drag
            self.move(p1+(e.globalPosition().toPoint()-p0))
    def _resize_press(self,e): self.resize_start=(e.globalPosition().toPoint(),self.size())
    def _resize_move(self,e):
        if self.resize_start:
            p0,s=self.resize_start
            d=e.globalPosition().toPoint()-p0
            self.resize(max(180,s.width()+d.x()),max(65,s.height()+d.y()))
    def mouseReleaseEvent(self,e): self.drag=self.resize_start=None
    def print_mode(self,on):
        self.moveh.setVisible(not on); self.handle.setVisible(not on)
        self.edit.setReadOnly(on)

class BulletinCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self.scale_factor=1.0
        self.setFixedSize(int(DW),int(DH))
        self.font_size=10
        self.edits={}
        for name,x,y,w,h,numeric in FIELDS:
            e=QLineEdit(self)
            e.setObjectName(name)
            e.setMaxLength(80)
            e.setAlignment(Qt.AlignCenter if numeric else Qt.AlignLeft|Qt.AlignVCenter)
            e.setStyleSheet("QLineEdit{border:0;background:transparent;color:#111;padding:0 3px;font-family:'Times New Roman';font-weight:700;}")
            self.edits[name]=e
        self.price=Sticker("PRIX À DÉBATTRE À .......... | À CAUSE DE : ................................. | ................................................",False,self)
        self.refusal=Sticker("PRODUIT REFUSÉ À CAUSE DE : | ................................................",True,self)
        self.price.hide(); self.refusal.hide()
        self.result_rows={}
        self.result_totals=(0.0,0.0,"")
        self.relayout(); self.set_font_size(10); self._place_stickers()
    def value(self,n): return self.edits[n].text().strip()
    def set_scale(self,z):
        self.scale_factor=max(.25,min(1.0,float(z)))
        self.setFixedSize(int(DW*self.scale_factor),int(DH*self.scale_factor))
        self.relayout(); self._place_stickers(); self.update()
    def _place_stickers(self):
        for s,x,y in ((self.price,690,570),(self.refusal,690,675)):
            s.move(int(x*self.scale_factor),int(y*self.scale_factor))
            s.resize(max(90,int(360*self.scale_factor)),max(30,int(100*self.scale_factor)))
    def relayout(self):
        z=self.scale_factor
        for n,x,y,w,h,_ in FIELDS: self.edits[n].setGeometry(int(x*z),int(y*z),int(w*z),int(h*z))
    def set_font_size(self,s):
        self.font_size=max(6,min(14,int(s)))
        px=max(7,int(self.font_size*1.333*self.scale_factor))
        for e in self.edits.values():
            e.setStyleSheet(f"QLineEdit{{border:0;background:transparent;color:#111;padding:0 3px;font-family:'Times New Roman';font-weight:700;font-size:{px}px;}}")
    def text(self,p,s,x,y,size=20,bold=False,w=520,align=Qt.AlignLeft):
        f=QFont("Times New Roman",size); f.setBold(bold); p.setFont(f); p.drawText(QRectF(x,y-size,w,size*1.55),align,s)
    def center(self,p,s,x,y,w,size=19,bold=False):
        self.text(p,s,x,y,size,bold,w,Qt.AlignCenter)
    def logo(self,p,x,y):
        pix=QPixmap()
        pix.loadFromData(base64.b64decode(LOGO_B64))
        p.drawPixmap(QRectF(x-45,y-45,x+45,y+45).toRect(),pix)
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing); p.fillRect(self.rect(),Qt.white)
        p.scale(self.scale_factor,self.scale_factor)
        self.draw_page(p); p.end()
    def draw_page(self,p):
        self.logo(p,70,72); self.logo(p,DW-70,72)
        self.center(p,"OFFICE ALGERIEN INTERPROFESSIONNEL DES CEREALES",115,82,1108,31,True)
        self.center(p,"Coopérative de Céréales et des Légumes Secs de BATNA",170,145,998,28,True)
        self.center(p,"Bulletin d'Agréage",330,205,678,38,True)
        self.text(p,"Espèce :",104,270,28,True,130); self.text(p,"Blé Dur",235,270,32,True,180)
        self.text(p,"Date :",700,300,28,True,100)
        head=[("Nom du producteur :",104,395,250),("Adresse :",104,430,160),("Point de collecte :",104,465,220),
              ("Nom de l'agréeur :",700,395,240),("Quantité :",700,430,160),("N° Bon d'entrée :",700,465,190)]
        for label,x,y,w in head: self.text(p,label,x,y,24,True,w)
        self.draw_table(p)
        self.text(p,"Référence : Décret n°88-152 du 26 juillet 1988 fixant les barèmes de bonification et de réfaction applicables aux céréales",104,1780,15,False,1050)
        self.text(p,"et aux légumes secs. 1ère partie : Relations entre producteurs et organismes stockeurs.",104,1800,15,False,900)
        self.text(p,"Producteur",105,1870,22,True,300); self.text(p,"N° de la carte d’identité",105,1920,21,True,330); self.text(p,"Agréeur",1030,1870,22,True,250)
    def draw_table(self,p):
        x0,xcat,x1,x2,x3,x4,x5,x6=75,180,525,655,760,925,1062,1160
        ys=[530,638,670,710,753,828,937,1005,1047,1084,1135,1184,1235,1274,1317,1367,1417,1471,1515,1576,1620,1670]
        p.setPen(QPen(QColor("#111"),1.5)); p.drawRect(QRectF(x0,ys[0],x6-x0,ys[-1]-ys[0]))
        for y in ys[1:-1]: p.drawLine(x0,y,x6,y)
        for x in (xcat,x1,x2,x3,x4,x5): p.drawLine(x,ys[0],x,ys[-1])
        self.center(p,"Paramètres",xcat,585,x1-xcat,24,True)
        self.center(p,"Limites",x1,560,x2-x1,22,True); self.center(p,"(sans",x1,584,x2-x1,13,True); self.center(p,"bonification ni",x1,600,x2-x1,13,True); self.center(p,"réfaction)",x1,616,x2-x1,13,True)
        self.center(p,"Valeurs",x2,585,x3-x2,22,True)
        self.center(p,"Bonification",x3,565,x4-x3,20,True); self.center(p,"(D.A.)",x3,588,x4-x3,18,True)
        self.center(p,"Réfaction",x4,565,x5-x4,20,True); self.center(p,"(D.A.)",x4,588,x5-x4,18,True)
        self.center(p,"Observation",x5,585,x6-x5,20,True)
        self.vertical(p,"Impuretés 1ère catégorie",126,750,1005)
        self.vertical(p,"Impuretés 2ème catégorie",126,1047,1417)
        self.vertical(p,"Grains\nmitadinés",126,1417,1670)
        rows=[
            (638,670,"Poids spécifique (kg/hl)","[76 - 80]","poids"),
            (670,710,"Teneur en eau (%)","≤ 17",None),(710,753,"Ergot (‰)","≤ 1",None),
            (753,828,"Matières qui passent à travers\nle tamis 20 mm x2.1mm (%)","-",None),
            (828,937,"Les débris végétaux et les\néléments minéraux (%)\nRetenus par le tamis 20 mm x2.1mm","-",None),
            (937,1005,"Graines nuisibles (%)","≤ 0,25",None),(1005,1047,"Total (%)","[1 - 3]","impur1"),
            (1047,1084,"Grains cassés (%)","≤ 5","casses"),(1084,1135,"Grains fortement boutés (%)","≤ 5","boutes"),
            (1135,1184,"Grains Roux (%)","-",None),(1184,1274,"Grains fortement mouchetés\n(%)","-",None),
            (1274,1317,"Grains punaisés (%)","-",None),(1317,1367,"Grains piqués (%)","-",None),
            (1367,1417,"Total (%)","≤ 10","impur2"),(1417,1471,"Grains mitadinés (%)","-","mitadin"),
            (1471,1515,"Blé tendre dans blé dur (%)","≤ 5","bleTendre"),(1515,1576,"Total (%)","[10 - 20]","mitadin")
        ]
        for top,bottom,label,limit,key in rows:
            cy=(top+bottom)/2+7
            lines=label.split("\\n")
            if len(lines)==1: self.text(p,label,195,cy,19,True,325)
            else:
                for i,line in enumerate(lines): self.text(p,line,195,cy+i*24,17 if i else 18,True,325)
            self.center(p,limit,x1,cy,x2-x1,19,True)
            if key and key in self.result_rows:
                b,r=self.result_rows[key]
                if b: self.center(p,f"{b:.2f}",x3,cy,x4-x3,18,True)
                if r: self.center(p,f"{r:.2f}",x4,cy,x5-x4,18,True)
        self.center(p,"Total des Bonifications et Réfactions",x0,1708,x2-x0,20,True)
        b,r,obs=self.result_totals
        if b or r:
            self.center(p,f"{b:.2f}",x3,1708,x4-x3,19,True); self.center(p,f"{r:.2f}",x4,1708,x5-x4,19,True)
            self.center(p,obs[:18],x5,1708,x6-x5,13,False)
    def vertical(self,p,text,x,top,bottom):
        p.save(); p.rotate(-90,x,(top+bottom)/2)
        for i,line in enumerate(text.split("\\n")): self.text(p,line,x,(top+bottom)/2+i*22,19,True,220,Qt.AlignCenter)
        p.restore()
    def update_results(self,r):
        bonus,refa,imp1,imp2,mit,rows,notes=r
        self.edits["impur1Total"].setText(f"{imp1:.2f}")
        self.edits["impur2Total"].setText(f"{imp2:.2f}")
        self.edits["mitadinTotal"].setText(f"{mit:.2f}")
        self.result_rows=rows
        self.result_totals=(bonus,refa,notes[0] if notes else "")
        self.update()

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bulletin d’Agréage — Edition professionnelle")
        self.resize(1500,960); self.setMinimumSize(1150,760)
        self.canvas=BulletinCanvas(); self.zoom=.48; self.font=10
        self.preview=QScrollArea(); self.preview.setWidget(self.canvas); self.preview.setWidgetResizable(False); self.preview.setAlignment(Qt.AlignCenter)
        side=QFrame(); side.setObjectName("side"); side.setMinimumWidth(320); side.setMaximumWidth(380)
        sl=QVBoxLayout(side); sl.setContentsMargins(20,20,20,20); sl.setSpacing(10)
        title=QLabel("Bulletin d’Agréage"); title.setObjectName("appTitle")
        sub=QLabel("Reproduction fidèle du formulaire de référence"); sub.setObjectName("subTitle")
        sl.addWidget(title); sl.addWidget(sub)
        box=QGroupBox("حالة الاستلام"); bl=QVBoxLayout(box)
        self.status=QComboBox(); self.status.addItems(["قابل للاستلام","مرفوض"]); bl.addWidget(self.status); sl.addWidget(box)
        fb=QGroupBox("حجم خط البيانات"); fl=QHBoxLayout(fb)
        fm=QToolButton(); fm.setText("−"); fp=QToolButton(); fp.setText("+"); self.fontLabel=QLabel("10"); self.fontLabel.setAlignment(Qt.AlignCenter)
        fl.addWidget(fm); fl.addWidget(self.fontLabel,1); fl.addWidget(fp); sl.addWidget(fb)
        zb=QGroupBox("المعاينة"); zl=QHBoxLayout(zb)
        zm=QToolButton(); zm.setText("−"); zp=QToolButton(); zp.setText("+"); fit=QPushButton("ملاءمة")
        zl.addWidget(zm); zl.addWidget(fit,1); zl.addWidget(zp); sl.addWidget(zb)
        sb=QGroupBox("الملصقات"); ssl=QVBoxLayout(sb)
        self.priceBtn=QPushButton("✎ تعديل ملصق PRIX À DÉBATTRE")
        self.refusalBtn=QPushButton("✎ تعديل ملصق الرفض")
        ssl.addWidget(self.priceBtn); ssl.addWidget(self.refusalBtn); sl.addWidget(sb)
        calc=QPushButton("حساب النتائج"); calc.setObjectName("primary")
        pdf=QPushButton("تصدير PDF"); pdf.setObjectName("pdf")
        sl.addWidget(calc); sl.addWidget(pdf)
        self.summary=QLabel("أدخل القيم ثم اضغط «حساب النتائج»."); self.summary.setWordWrap(True); self.summary.setObjectName("summary"); sl.addWidget(self.summary)
        sl.addStretch(1)
        sl.addWidget(QLabel("يمكن تحريك الملصق من ✥ وتغيير حجمه من ↘.\nوالنص يمكن تعديله من أزرار التعديل أو بالنقر مرتين."))
        root=QHBoxLayout(self); root.setContentsMargins(0,0,0,0); root.addWidget(side); root.addWidget(self.preview,1)
        self.status.currentIndexChanged.connect(self.status_changed)
        calc.clicked.connect(self.do_calc); pdf.clicked.connect(self.export_pdf)
        self.priceBtn.clicked.connect(lambda:self.canvas.price.edit_text_dialog())
        self.refusalBtn.clicked.connect(lambda:self.canvas.refusal.edit_text_dialog())
        fm.clicked.connect(lambda:self.set_font(self.font-1)); fp.clicked.connect(lambda:self.set_font(self.font+1))
        zm.clicked.connect(lambda:self.set_zoom(self.zoom-.05)); zp.clicked.connect(lambda:self.set_zoom(self.zoom+.05)); fit.clicked.connect(self.fit)
        self.status_changed(0); self.fit()
    def set_font(self,s):
        self.font=max(6,min(14,int(s))); self.canvas.set_font_size(self.font); self.fontLabel.setText(str(self.font))
    def set_zoom(self,z):
        self.zoom=max(.25,min(.85,z)); self.canvas.set_scale(self.zoom)
    def fit(self):
        avail=max(600,self.preview.viewport().height()-30); self.zoom=min(.76,max(.30,avail/DH)); self.canvas.set_scale(self.zoom)
    def resizeEvent(self,e): super().resizeEvent(e); self.fit()
    def status_changed(self,i):
        self.canvas.refusal.setVisible(i==1); self.canvas.update()
    def do_calc(self):
        r=calculate(self.canvas.value); self.canvas.update_results(r)
        bonus,refa,imp1,imp2,mit,rows,notes=r
        self.canvas.price.setVisible(imp1>6 or imp2>20)
        state="مرفوض" if self.status.currentIndex()==1 else "قابل للاستلام"
        txt=f"<b>{state}</b><br>Bonification: <b>{bonus:.2f} DA</b><br>Réfaction: <b>{refa:.2f} DA</b><br>Solde: <b>{bonus-refa:.2f} DA</b><br><br>Imp. 1ère: {imp1:.2f}% • Imp. 2ème: {imp2:.2f}% • Mitadin+tendre: {mit:.2f}%"
        if notes: txt += "<br><br>" + "<br>".join("• "+n for n in notes)
        self.summary.setText(txt)
    def export_pdf(self):
        self.do_calc()
        path=os.path.join(os.path.expanduser("~"),"Downloads",f"Bulletin_Agreage_{datetime.datetime.now():%Y%m%d_%H%M%S}.pdf")
        os.makedirs(os.path.dirname(path),exist_ok=True)
        oldzoom=self.zoom; self.canvas.set_scale(1.0)
        self.canvas.price.print_mode(True); self.canvas.refusal.print_mode(True)
        printer=QPrinter(QPrinter.HighResolution); printer.setOutputFormat(QPrinter.PdfFormat); printer.setOutputFileName(path); printer.setPageSize(QPrinter.A4); printer.setPageMargins(0,0,0,0,QPrinter.Millimeter)
        painter=QPainter(printer)
        target=QRectF(0,0,printer.pageRect(QPrinter.DevicePixel).width(),printer.pageRect(QPrinter.DevicePixel).height())
        painter.scale(target.width()/DW,target.height()/DH)
        self.canvas.render(painter,QPoint(0,0),QRectF(0,0,DW,DH).toRect())
        painter.end()
        self.canvas.price.print_mode(False); self.canvas.refusal.print_mode(False)
        self.canvas.set_scale(oldzoom); self.fit()
        QMessageBox.information(self,"تم التصدير","تم حفظ الملف في مجلد Downloads:\n"+path)

if __name__=="__main__":
    app=QApplication(sys.argv); app.setLayoutDirection(Qt.RightToLeft)
    app.setStyleSheet("""
        QWidget{font-family:'Segoe UI';font-size:10pt;color:#17202a;}
        QWidget#side{background:#f7f9fc;border-left:1px solid #dfe5ec;}
        QLabel#appTitle{font-size:23pt;font-weight:800;color:#16263d;}
        QLabel#subTitle{color:#697586;margin-bottom:8px;}
        QGroupBox{border:1px solid #dbe2ea;border-radius:12px;margin-top:8px;padding:12px;background:#fff;font-weight:700;}
        QGroupBox::title{subcontrol-origin:margin;left:12px;padding:0 5px;color:#506070;}
        QComboBox,QLineEdit{background:#fff;border:1px solid #cfd8e3;border-radius:8px;padding:7px;}
        QPushButton{background:#fff;border:1px solid #cfd8e3;border-radius:9px;padding:10px 12px;font-weight:700;}
        QPushButton:hover{background:#f1f5f9;}
        QPushButton#primary{background:#2457d6;color:white;border:0;font-size:11pt;}
        QPushButton#pdf{background:#16263d;color:white;border:0;font-size:11pt;}
        QToolButton{background:#fff;border:1px solid #cfd8e3;border-radius:8px;min-width:34px;min-height:30px;font-weight:800;}
        QLabel#summary{background:#fff;border:1px solid #dbe2ea;border-radius:12px;padding:12px;color:#334155;}
        QScrollArea{background:#eef1f5;border:0;}
        QFrame#priceSticker{background:#fff4cf;border:2px solid #c28a19;border-radius:10px;}
        QFrame#refusalSticker{background:#ffe7ec;border:2px solid #d52b42;border-radius:10px;}
    """)
    w=MainWindow(); w.show(); sys.exit(app.exec())
