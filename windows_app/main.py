import sys, os, math, datetime
from PySide6.QtCore import Qt, QRectF, QPoint, QSize
from PySide6.QtGui import QPainter, QPen, QFont, QColor, QFontMetrics
from PySide6.QtWidgets import (
    QApplication, QWidget, QLineEdit, QPushButton, QLabel, QComboBox,
    QVBoxLayout, QHBoxLayout, QScrollArea, QMessageBox, QFrame,
    QSpinBox, QGroupBox, QGridLayout, QSizePolicy, QToolButton
)
from PySide6.QtPrintSupport import QPrinter

# Design coordinate system follows the Android/reference sheet.
DW, DH = 1338.0, 1900.0

FIELDS = [
    ("date",805,246,225,30,False), ("producteur",380,336,155,30,False),
    ("adresse",250,373,285,30,False), ("pointCollecte",340,410,195,30,False),
    ("agreur",940,336,110,30,False), ("quantite",835,373,175,30,False),
    ("numeroBon",885,410,165,30,False), ("carteIdentite",110,1778,360,40,False),
    ("poids",655,642,105,24,True), ("humidite",655,674,105,32,True),
    ("ergot",655,714,105,35,True), ("tamis",655,758,105,65,True),
    ("debris",655,833,105,99,True), ("grainesNuisibles",655,941,105,60,True),
    ("impur1Total",655,1009,105,34,True), ("casses",655,1050,105,31,True),
    ("boutes",655,1088,105,43,True), ("roux",655,1139,105,41,True),
    ("mouchetes",655,1239,105,31,True), ("punaises",655,1279,105,33,True),
    ("piques",655,1322,105,41,True), ("impur2Total",655,1372,105,32,True),
    ("mitadin",655,1422,105,44,True), ("bleTendre",655,1475,105,36,True),
    ("mitadinTotal",655,1520,105,52,True)
]

def num(s):
    try: return float((s or "").replace(",", ".").strip())
    except: return None

def tranches(exces, taille):
    return 0 if exces <= 0 else math.ceil(exces / taille)

def calculate(v):
    p,h,e=num(v("poids")),num(v("humidite")),num(v("ergot"))
    t,d,gn=[num(v(k)) or 0 for k in ("tamis","debris","grainesNuisibles")]
    c,b,r,m,pu,pi=[num(v(k)) or 0 for k in ("casses","boutes","roux","mouchetes","punaises","piques")]
    imp1,imp2=t+d+gn,c+b+r+m+pu+pi
    mit,tender=num(v("mitadin")) or 0,num(v("bleTendre")) or 0
    mit_total=mit+tender
    bonus=refa=0.0; rows={}; notes=[]
    def add(k,bb=0,rr=0):
        nonlocal bonus,refa
        if bb or rr: rows[k]=(bb,rr)
        bonus+=bb; refa+=rr
    if p is not None:
        if p>80:
            add("poids",tranches(min(p,82)-80,.25)*.15+tranches(min(p,83)-82,.25)*.10+
                (tranches(min(p,84)-83,.25)+tranches(max(p-84,0),.25))*.05)
        elif 72<=p<76:
            add("poids",rr=tranches(76-max(p,75),.25)*.10+tranches(75-max(p,74),.25)*.20+tranches(74-p,.25)*.30)
        elif p<72: notes.append("Poids spécifique inférieur à 72 kg/hl : hors critère sain, loyal et marchand.")
    if h is not None and h>17: notes.append("Humidité supérieure à 17 % : hors limite.")
    if e is not None and e>1: notes.append("Ergot supérieur à 1 ‰ : hors limite.")
    if imp1<1: add("impur1",bb=tranches(1-imp1,.25)*.125)
    elif 3<imp1<=6: add("impur1",rr=tranches(imp1-3,.25)*.125)
    elif imp1>6: notes.append("Impuretés 1ère catégorie > 6 % : prix à débattre.")
    if c>5: add("casses",rr=tranches(c-5,.25)*.075)
    if b>5: add("boutes",rr=tranches(b-5,1)*.05)
    if 10<imp2<=20: add("impur2",rr=tranches(imp2-10,1)*.50)
    elif imp2>20: notes.append("Impuretés 2ème catégorie > 20 % : hors barème.")
    if 0<=mit_total<=10: add("mitadin",bb=.25)
    elif 20<mit_total<=70: add("mitadin",rr=tranches(mit_total-20,1)*.05)
    elif mit_total>70: notes.append("Mitadin > 70 % : paiement au prix du blé tendre avec son barème.")
    if tender>10: notes.append("Blé tendre > 10 % : paiement du blé dur au prix du blé tendre avec son barème.")
    return bonus,refa,imp1,imp2,mit_total,rows,notes

class Sticker(QFrame):
    def __init__(self,text,refusal=False,parent=None):
        super().__init__(parent); self.refusal=refusal; self.drag=None; self.resize_start=None
        self.setObjectName("refusalSticker" if refusal else "priceSticker")
        self.edit=QLineEdit(text,self); self.edit.setAlignment(Qt.AlignCenter)
        self.edit.setStyleSheet("QLineEdit{border:0;background:transparent;padding:8px;font-weight:700;}")
        self.handle=QLabel("↘",self); self.moveh=QLabel("✥",self)
        for w in (self.handle,self.moveh): w.setAlignment(Qt.AlignCenter)
        self.handle.setStyleSheet("background:rgba(0,0,0,18);font-size:18px;border:0;")
        self.moveh.setStyleSheet("background:rgba(0,0,0,12);font-size:16px;border:0;")
        self.resize(360,100)
        self.moveh.mousePressEvent=self._move_press; self.moveh.mouseMoveEvent=self._move_move
        self.handle.mousePressEvent=self._resize_press; self.handle.mouseMoveEvent=self._resize_move
    def resizeEvent(self,e):
        self.edit.setGeometry(8,6,max(1,self.width()-58),max(1,self.height()-12))
        self.moveh.setGeometry(self.width()-50,0,50,40); self.handle.setGeometry(self.width()-54,self.height()-54,54,54)
    def _move_press(self,e): self.drag=(e.globalPosition().toPoint(),self.pos())
    def _move_move(self,e):
        if self.drag:
            p0,p1=self.drag; self.move(p1+(e.globalPosition().toPoint()-p0))
    def _resize_press(self,e): self.resize_start=(e.globalPosition().toPoint(),self.size())
    def _resize_move(self,e):
        if self.resize_start:
            p0,s=self.resize_start; d=e.globalPosition().toPoint()-p0
            self.resize(max(180,s.width()+d.x()),max(65,s.height()+d.y()))
    def mouseReleaseEvent(self,e): self.drag=self.resize_start=None
    def print_mode(self,on):
        self.moveh.setVisible(not on); self.handle.setVisible(not on); self.edit.setReadOnly(on)

class BulletinCanvas(QWidget):
    def __init__(self):
        super().__init__(); self.setFixedSize(int(DW),int(DH)); self.font_size=10
        self.edits={}
        for name,x,y,w,h,numeric in FIELDS:
            e=QLineEdit(self); e.setObjectName(name); e.setMaxLength(80)
            e.setAlignment(Qt.AlignCenter if numeric else Qt.AlignLeft|Qt.AlignVCenter)
            e.setStyleSheet("QLineEdit{border:0;background:transparent;color:#111;padding:0 3px;}")
            self.edits[name]=e
        self.price=Sticker("PRIX À DÉBATTRE À ..........\nÀ CAUSE DE : .................................\n................................................",False,self)
        self.refusal=Sticker("PRODUIT REFUSÉ À CAUSE DE :\n................................................",True,self)
        self.price.move(690,548); self.refusal.move(690,650); self.price.hide(); self.refusal.hide()
        self.relayout(); self.set_font_size(10)
    def value(self,n): return self.edits[n].text().strip()
    def relayout(self):
        for n,x,y,w,h,_ in FIELDS: self.edits[n].setGeometry(x,y,w,h)
    def set_font_size(self,s):
        self.font_size=max(6,min(14,int(s)))
        for e in self.edits.values():
            e.setStyleSheet(f"QLineEdit{{border:0;background:transparent;color:#111;padding:0 3px;font-size:{self.font_size}pt;}}")
    def text(self,p,s,x,y,size=20,bold=False,w=520,align=Qt.AlignLeft):
        f=QFont("Times New Roman",size); f.setBold(bold); p.setFont(f)
        p.drawText(QRectF(x,y-size,w,size*1.55),align,s)
    def center(self,p,s,x,y,w,size=19,bold=False):
        self.text(p,s,x,y,size,bold,w,Qt.AlignCenter)
    def logo(self,p,x,y,flip=False):
        p.save(); p.setPen(QPen(QColor("#111"),4)); p.setBrush(Qt.NoBrush)
        if flip:
            x=DW-x-92
        p.drawArc(QRectF(x+10,y+20,70,44),20*16,140*16)
        p.drawLine(x+18,y+61,x+73,y+61); p.drawLine(x+45,y+10,x+34,y+55); p.drawLine(x+45,y+10,x+58,y+55)
        p.restore()
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing); p.fillRect(self.rect(),Qt.white)
        self.draw_page(p); p.end()
    def draw_page(self,p):
        self.logo(p,18,18); self.logo(p,18,18,True)
        self.center(p,"OFFICE ALGERIEN INTERPROFESSIONNEL DES CEREALES",170,58,1000,23,True)
        self.center(p,"Coopérative de Céréales et des Légumes Secs de BATNA",170,92,1000,21,True)
        self.center(p,"Bulletin d’Agréage",330,139,680,32,True)
        self.text(p,"Espèce : Blé Dur",105,190,22,True)
        head=[("Date :",700,260,340),("Nom du producteur :",105,350,500),("Adresse :",105,387,500),
              ("Point de collecte :",105,424,500),("Nom de l’agréeur :",700,350,350),("Quantité :",700,387,350),("N° Bon d'entrée :",700,424,350)]
        for label,x,y,w in head:
            self.text(p,label,x,y,20,True,170); p.setPen(QPen(QColor("#777"),1,Qt.DotLine)); p.drawLine(x+170,y+3,x+w,y+3); p.setPen(QColor("#111"))
        x0,x1,x2,x3,x4,x5,x6=102,530,653,760,927,1063,1155
        ys=[530,638,670,710,753,828,937,1005,1047,1084,1135,1184,1235,1274,1317,1367,1417,1471,1515,1576,1618]
        p.setPen(QPen(QColor("#222"),1.4)); p.drawRect(QRectF(x0,ys[0],x6-x0,ys[-1]-ys[0]))
        for y in ys[1:-1]: p.drawLine(x0,y,x6,y)
        for x in (x1,x2,x3,x4,x5): p.drawLine(x,ys[0],x,ys[-1])
        self.center(p,"Paramètres",x0,575,x1-x0,24,True); self.center(p,"Limites",x1,557,x2-x1,22,True)
        self.center(p,"(sans",x1,582,x2-x1,14,True); self.center(p,"bonification ni",x1,599,x2-x1,14,True); self.center(p,"réfaction)",x1,616,x2-x1,14,True)
        self.center(p,"Valeurs",x2,575,x3-x2,22,True); self.center(p,"Bonification",x3,560,x4-x3,20,True); self.center(p,"(D.A.)",x3,585,x4-x3,18,True)
        self.center(p,"Réfaction",x4,560,x5-x4,20,True); self.center(p,"(D.A.)",x4,585,x5-x4,18,True); self.center(p,"Observation",x5,575,x6-x5,20,True)
        labels=[(638,670,"Poids spécifique (kg/hl)","[76 - 80]"),(670,710,"Teneur en eau (%)","≤ 17"),(710,753,"Ergot (‰)","≤ 1"),
        (937,1005,"Graines nuisibles (%)","≤ 0,25"),(1047,1084,"Grains cassés (%)","≤ 5"),(1084,1135,"Grains fortement boutés (%)","≤ 5"),
        (1135,1184,"Grains Roux (%)","-"),(1274,1317,"Grains punaisés (%)","-"),(1317,1367,"Grains piqués (%)","-")]
        for a,b,l,lim in labels:
            self.text(p,l,145,(a+b)/2+7,18,True,380); self.center(p,lim,530,(a+b)/2+7,123,19,True)
        self.text(p,"Matières qui passent à travers\nle tamis 20 mm x2.1mm (%)",145,790,17,True,350)
        self.text(p,"Les débris végétaux et les\néléments minéraux (%)",145,870,17,True,350)
        self.text(p,"Total (%)",145,1032,19,True,380); self.center(p,"[1 - 3]",530,1032,123,19,True)
        self.text(p,"Grains fortement mouchetés (%)",145,1260,18,True,380)
        self.text(p,"Total (%)",145,1392,19,True,380); self.center(p,"≤ 10",530,1392,123,19,True)
        self.text(p,"Grains mitadinés (%)",145,1450,19,True,380); self.center(p,"-",530,1450,123,19,True)
        self.text(p,"Blé tendre dans blé dur (%)",145,1498,18,True,380); self.center(p,"≤ 5",530,1498,123,19,True)
        self.text(p,"Total (%)",145,1548,19,True,380); self.center(p,"[10 - 20]",530,1548,123,19,True)
        self.center(p,"Impuretés 1ère catégorie",316,875,210,18,True); self.center(p,"Impuretés 2ème catégorie",316,1200,210,18,True)
        self.center(p,"Grains mitadinés",316,1490,210,18,True)
        self.text(p,"Total des Bonifications et Réfactions",102,1605,20,True,500)
        self.text(p,"Référence : Décret n°88-152 du 26 juillet 1988",104,1660,15,False,500)
        self.text(p,"Producteur",105,1740,22,True,300); self.text(p,"N° de la carte d’identité",105,1800,21,True,330); self.text(p,"Agréeur",1030,1740,22,True,250)
    def update_results(self,r):
        bonus,refa,imp1,imp2,mit,rows,notes=r
        self.edits["impur1Total"].setText(f"{imp1:.2f}")
        self.edits["impur2Total"].setText(f"{imp2:.2f}")
        self.edits["mitadinTotal"].setText(f"{mit:.2f}")
        self.update()

class MainWindow(QWidget):
    def __init__(self):
        super().__init__(); self.setWindowTitle("Bulletin d’Agréage"); self.resize(1500,960); self.setMinimumSize(1120,760)
        self.canvas=BulletinCanvas(); self.zoom=0.48; self.font=10
        self.preview=QScrollArea(); self.preview.setWidget(self.canvas); self.preview.setWidgetResizable(False); self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setStyleSheet("QScrollArea{background:#eef1f5;border:0;} QScrollBar:vertical{width:12px;} QScrollBar:horizontal{height:12px;}")
        side=QFrame(); side.setObjectName("side"); side.setMinimumWidth(300); side.setMaximumWidth(360)
        sl=QVBoxLayout(side); sl.setContentsMargins(20,20,20,20); sl.setSpacing(12)
        title=QLabel("Bulletin d’Agréage"); title.setObjectName("appTitle")
        sub=QLabel("Edition Windows • مطابق لتصميم الاستمارة"); sub.setObjectName("subTitle")
        sl.addWidget(title); sl.addWidget(sub)
        self.status=QComboBox(); self.status.addItems(["قابل للاستلام","مرفوض"])
        box=QGroupBox("الحالة"); bl=QVBoxLayout(box); bl.addWidget(self.status); sl.addWidget(box)
        fb=QGroupBox("حجم خط البيانات"); fl=QHBoxLayout(fb)
        minus=QToolButton(); minus.setText("−"); plus=QToolButton(); plus.setText("+")
        self.fontLabel=QLabel("10"); self.fontLabel.setAlignment(Qt.AlignCenter)
        fl.addWidget(minus); fl.addWidget(self.fontLabel,1); fl.addWidget(plus); sl.addWidget(fb)
        zbox=QGroupBox("المعاينة"); zl=QHBoxLayout(zbox)
        zm=QToolButton(); zm.setText("−"); zp=QToolButton(); zp.setText("+"); fit=QPushButton("ملاءمة")
        zl.addWidget(zm); zl.addWidget(fit,1); zl.addWidget(zp); sl.addWidget(zbox)
        calc=QPushButton("حساب النتائج"); calc.setObjectName("primary")
        pdf=QPushButton("تصدير PDF"); pdf.setObjectName("pdf")
        sl.addWidget(calc); sl.addWidget(pdf)
        self.summary=QLabel("أدخل القيم ثم اضغط «حساب النتائج»."); self.summary.setWordWrap(True); self.summary.setObjectName("summary"); sl.addWidget(self.summary)
        sl.addStretch(1)
        foot=QLabel("Bulletin d’Agréage • Windows\nنفس منطق الحساب المستخدم في النسخة الحالية")
        foot.setObjectName("footer"); sl.addWidget(foot)
        root=QHBoxLayout(self); root.setContentsMargins(0,0,0,0); root.addWidget(side); root.addWidget(self.preview,1)
        self.status.currentIndexChanged.connect(self.status_changed); calc.clicked.connect(self.do_calc); pdf.clicked.connect(self.export_pdf)
        minus.clicked.connect(lambda:self.set_font(self.font-1)); plus.clicked.connect(lambda:self.set_font(self.font+1))
        zm.clicked.connect(lambda:self.set_zoom(self.zoom-0.05)); zp.clicked.connect(lambda:self.set_zoom(self.zoom+0.05)); fit.clicked.connect(self.fit)
        self.status_changed(0); self.fit()
    def set_font(self,s):
        self.font=max(6,min(14,int(s))); self.canvas.set_font_size(self.font); self.fontLabel.setText(str(self.font))
    def set_zoom(self,z):
        self.zoom=max(.25,min(.85,z)); self.canvas.setFixedSize(int(DW*self.zoom),int(DH*self.zoom))
        # Paint and child geometry are in design coordinates; scale the widget visually by resizing is not enough.
        # Instead use a graphics-like transform via the preview viewport's zoom factor.
        self.canvas.setMinimumSize(int(DW*self.zoom),int(DH*self.zoom))
        self.canvas.resize(int(DW*self.zoom),int(DH*self.zoom))
    def fit(self):
        avail=max(600,self.preview.viewport().height()-30)
        self.zoom=min(.78,max(.32,avail/DH))
        self.canvas.setFixedSize(int(DW*self.zoom),int(DH*self.zoom))
    def resizeEvent(self,e): super().resizeEvent(e); self.fit()
    def status_changed(self,i):
        self.canvas.refusal.setVisible(i==1); self.canvas.update()
    def do_calc(self):
        r=self.canvas.update_results(calculate(self.canvas.value)); bonus,refa,imp1,imp2,mit,rows,notes=r
        urgent=bool(notes) or imp1>6 or imp2>20
        self.canvas.price.setVisible(imp1>6 or imp2>20)
        state="مرفوض" if self.status.currentIndex()==1 else "قابل للاستلام"
        txt=f"<b>{state}</b><br>Bonification: <b>{bonus:.2f} DA</b><br>Réfaction: <b>{refa:.2f} DA</b><br>Solde: <b>{bonus-refa:.2f} DA</b><br><br>Imp. 1ère: {imp1:.2f}% • Imp. 2ème: {imp2:.2f}% • Mitadin+tendre: {mit:.2f}%"
        if notes: txt += "<br><br>" + "<br>".join("• "+n for n in notes)
        self.summary.setText(txt)
    def export_pdf(self):
        self.do_calc()
        path=os.path.join(os.path.expanduser("~"),"Downloads",f"Bulletin_Agreage_{datetime.datetime.now():%Y%m%d_%H%M%S}.pdf")
        os.makedirs(os.path.dirname(path),exist_ok=True)
        # PDF export uses the full design canvas, independent of preview zoom.
        oldsize=self.canvas.size(); self.canvas.setFixedSize(int(DW),int(DH))
        self.canvas.price.print_mode(True); self.canvas.refusal.print_mode(True)
        printer=QPrinter(QPrinter.HighResolution); printer.setOutputFormat(QPrinter.PdfFormat); printer.setOutputFileName(path); printer.setPageSize(QPrinter.A4); printer.setPageMargins(0,0,0,0,QPrinter.Millimeter)
        painter=QPainter(printer); target=QRectF(0,0,printer.pageRect(QPrinter.DevicePixel).width(),printer.pageRect(QPrinter.DevicePixel).height())
        painter.scale(target.width()/DW,target.height()/DH); self.canvas.render(painter,QPoint(0,0),QRect(0,0,int(DW),int(DH))); painter.end()
        self.canvas.price.print_mode(False); self.canvas.refusal.print_mode(False)
        self.canvas.setFixedSize(*oldsize); self.fit()
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
        QComboBox:focus,QLineEdit:focus{border:1px solid #5b8def;}
        QPushButton{background:#fff;border:1px solid #cfd8e3;border-radius:9px;padding:10px 14px;font-weight:700;}
        QPushButton:hover{background:#f1f5f9;}
        QPushButton#primary{background:#2457d6;color:white;border:0;font-size:11pt;}
        QPushButton#pdf{background:#16263d;color:white;border:0;font-size:11pt;}
        QToolButton{background:#fff;border:1px solid #cfd8e3;border-radius:8px;min-width:34px;min-height:30px;font-weight:800;}
        QLabel#summary{background:#fff;border:1px solid #dbe2ea;border-radius:12px;padding:12px;color:#334155;}
        QLabel#footer{color:#7b8794;font-size:8pt;}
        QScrollArea{background:#eef1f5;}
        QFrame#priceSticker{background:#fff4cf;border:2px solid #c28a19;border-radius:10px;}
        QFrame#refusalSticker{background:#ffe7ec;border:2px solid #d52b42;border-radius:10px;}
    """)
    w=MainWindow(); w.show(); sys.exit(app.exec())
