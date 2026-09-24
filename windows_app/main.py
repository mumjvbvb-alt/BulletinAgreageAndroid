import sys, os, json, math, datetime
from PySide6.QtCore import Qt, QRectF, QPoint, QSettings, QRegularExpression
from PySide6.QtGui import QPainter, QPen, QFont, QColor, QPixmap
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel, QLineEdit, QComboBox,
    QPushButton, QVBoxLayout, QHBoxLayout, QFormLayout, QScrollArea,
    QGroupBox, QFileDialog, QMessageBox, QSplitter, QTabWidget, QTextEdit
)
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtGui import QRegularExpressionValidator

PW, PH = 794, 1123
NAV_W, PANEL_W = 190, 360
GENERAL = [
    ("producteur","Nom du producteur"),("adresse","Adresse"),("point","Point de collecte"),
    ("agreur","Nom de l’agréeur"),("quantite","Quantité (Qx)"),("bon","N° Bon d’entrée"),
    ("carte","N° de la carte d’identité")]
QUALITY = [
    ("poids","Poids spécifique (kg/hl)","76 - 80"),("humidite","Teneur en eau (%)","≤ 17"),
    ("ergot","Ergot (%)","≤ 1"),("tamis","Matières passant au tamis 20 mm x 2.1 mm (%)","-"),
    ("debris","Débris végétaux et éléments minéraux (%)","-"),("nuisibles","Graines nuisibles (%)","≤ 0,25"),
    ("casses","Grains cassés (%)","≤ 5"),("boutes","Grains fortement boutés (%)","≤ 5"),
    ("roux","Grains roux (%)","-"),("mouchetes","Grains fortement mouchetés (%)","-"),
    ("punaises","Grains punaisés (%)","-"),("piques","Grains piqués (%)","-"),
    ("mitadin","Grains mitadinés (%)","-"),("tendre","Blé tendre dans blé dur (%)","≤ 5")]

def fnum(v):
    try:return float(str(v).replace(",","."))
    except:return None
def steps(excess,step):return 0 if excess<=0 else math.ceil(excess/step-1e-9)

def calculate(q, espece="Blé Dur"):
    v={k:(fnum(q.get(k)) or 0.0) for k,_,_ in QUALITY}
    bonus=red=0.0; rows={}; notes=[]
    def add(k,b=0.0,r=0.0):
        nonlocal bonus,red
        bonus+=b; red+=r; rows[k]=(b,r)
    p,h,e=fnum(q.get("poids")),fnum(q.get("humidite")),fnum(q.get("ergot"))
    if espece=="Blé Dur":
        if p is not None:
            if p>80: add("poids",steps(p-80,.25)*.15)
            elif 72<=p<76: add("poids",r=steps(76-p,.25)*.10)
            elif p<72: notes.append("Poids spécifique inférieur à 72 kg/hl : hors limite.")
        if h is not None and h>17: notes.append("Humidité supérieure à 17 % : hors limite.")
        if e is not None and e>1: notes.append("Ergot supérieur à 1 ‰ : hors limite.")
        i1=v["tamis"]+v["debris"]+v["nuisibles"]
        if i1<1: add("imp1",b=steps(1-i1,.25)*.125)
        elif 3<i1<=6: add("imp1",r=steps(i1-3,.25)*.125)
        elif i1>6: notes.append("Impuretés 1ère catégorie > 6 % : prix à débattre.")
        if v["casses"]>5: add("casses",r=steps(v["casses"]-5,.25)*.075)
        if v["boutes"]>5: add("boutes",r=min(.50,steps(v["boutes"]-5,1)*.05))
        i2=v["casses"]+v["boutes"]+v["roux"]+v["mouchetes"]+v["punaises"]+v["piques"]
        if 10<i2<=20: add("imp2",r=steps(i2-10,1)*.50)
        elif i2>20: notes.append("Impuretés 2ème catégorie > 20 % : prix à débattre.")
        mit=v["mitadin"]+v["tendre"]
        if 0<mit<=10: add("mitadin",b=.25)
        elif 20<mit<=70: add("mitadin",r=steps(mit-20,1)*.05)
        elif mit>70: notes.append("Mitadin > 70 % : paiement au prix du blé tendre avec son barème.")
        return bonus,red,i1,i2,mit,rows,notes
    if espece=="Blé Tendre":
        if p is not None:
            if p>77: add("poids",b=steps(min(p,78)-77,.25)*.10+steps(max(min(p,80)-78,0),.25)*.05+steps(max(min(p,83)-80,0),.25)*.02)
            elif 69<=p<74: add("poids",r=steps(min(74-p,1),.25)*.04+steps(min(max(73-p,0),1),.25)*.10+steps(max(70-p,0),.25)*.20)
            elif p<69: notes.append("Poids spécifique inférieur à 69 kg/hl : hors limite.")
        if h is not None and h>17: notes.append("Humidité supérieure à 17 % : hors limite.")
        if e is not None and e>0.01: notes.append("Ergot supérieur à 0,01 ‰ : prix à débattre.")
        i1=v["tamis"]+v["debris"]+v["nuisibles"]
        if i1<1: add("imp1",b=steps(1-i1,.25)*.12)
        elif 3<i1<=6: add("imp1",r=steps(i1-3,.25)*.12)
        elif i1>6: notes.append("Impuretés 1ère catégorie > 6 % : prix à débattre.")
        if v["casses"]>4: add("casses",r=steps(v["casses"]-4,.25)*.04)
        if v["punaises"]>2: add("punaises",r=steps(v["punaises"]-2,.25)*.08)
        if v["boutes"]>0: add("boutes",r=steps(v["boutes"],.25)*.40)
        if v["faibleBoutes"]>0: add("faibleBoutes",r=steps(v["faibleBoutes"],.25)*.20)
        i2=v["casses"]+v["punaises"]+v["boutes"]+v["faibleBoutes"]+v["mouchetes"]+v["etrangers"]
        if 6<i2<=15: add("imp2",r=steps(i2-6,.25)*.05)
        elif i2>15: notes.append("Impuretés 2ème catégorie > 15 % : prix à débattre.")
        return bonus,red,i1,i2,0,rows,notes
    if p is not None:
        if p>62: add("poids",b=steps(p-62,.5)*.24)
        elif p<58: add("poids",r=steps(58-p,.5)*.12)
    if e is not None and e>1: notes.append("Ergot supérieur à 1 ‰ : hors limite.")
    imp=v["sansValeur"]+v["inertes"]
    if imp>2: add("impDiverses",r=steps(imp-2,.5)*.12)
    return bonus,red,imp,0,0,rows,notes
class Sticker(QFrame):
    def __init__(self,title,text,accent,parent):
        super().__init__(parent); self.drag=None; self.accent=accent
        lay=QVBoxLayout(self); lay.setContentsMargins(10,6,10,6)
        self.title=QLabel(title); self.title.setStyleSheet(f"color:{accent};font-weight:800")
        self.edit=QLineEdit(text); self.edit.setStyleSheet("border:0;background:transparent;font-weight:700")
        lay.addWidget(self.title); lay.addWidget(self.edit); self.resize(345,52)
    def mousePressEvent(self,e):
        if e.button()==Qt.LeftButton:self.drag=(e.globalPosition().toPoint(),self.pos())
    def mouseMoveEvent(self,e):
        if self.drag:
            a,b=self.drag; self.move(b+e.globalPosition().toPoint()-a)
    def mouseReleaseEvent(self,e):self.drag=None
    def wheelEvent(self,e):
        if e.modifiers()&Qt.ControlModifier:
            z=1.05 if e.angleDelta().y()>0 else .95
            self.resize(max(190,int(self.width()*z)),max(55,int(self.height()*z)))
        else:super().wheelEvent(e)

class InvoicePage(QWidget):
    def __init__(self):
        super().__init__(); self.zoom=1.; self.data={}; self.values={}; self.result=None
        self.settings=QSettings("OAIC","BulletinAgreage")
        self.base_font_size=int(self.settings.value("documentFontSize",9))
        self.logo=QPixmap(os.path.join(os.path.dirname(__file__),"logo.svg"))
        self.setMinimumSize(PW,PH)
        self.price=Sticker("PRIX À DÉBATTRE","PRIX À DÉBATTRE À .......... — À CAUSE DE : ................","#a76b00",self)
        self.refusal=Sticker("PRODUIT REFUSÉ À CAUSE DE","........................................................","#c51f3a",self)
        self.load_stickers()
        self.price.show()
        self.refusal.show()
    def load_stickers(self):
        for s,k,d in [(self.price,"price",QPoint(42,246)),(self.refusal,"refusal",QPoint(407,246))]:
            s.setGeometry(self.settings.value(k+"X",d.x(),int),self.settings.value(k+"Y",d.y(),int),
                          self.settings.value(k+"W",285,int),self.settings.value(k+"H",72,int))
            s.edit.setText(self.settings.value(k+"Text",s.edit.text()))
        self.price.show(); self.refusal.show()
    def save_stickers(self):
        for s,k in [(self.price,"price"),(self.refusal,"refusal")]:
            for n,v in [("X",s.x()),("Y",s.y()),("W",s.width()),("H",s.height()),("Text",s.edit.text())]:
                self.settings.setValue(k+n,v)
    def set_zoom(self,z):
        self.zoom=max(.5,min(1.4,z)); self.setFixedSize(int(PW*self.zoom),int(PH*self.zoom)); self.update()
    def txt(self,p,s,x,y,w=200,size=9,bold=False,align=Qt.AlignLeft):
        size=min(float(size), float(self.base_font_size) if size >= 8 else float(size))
        f=QFont("Times New Roman",size); f.setBold(bold); p.setFont(f)
        text=str(s or "")
        if text:
            fm=p.fontMetrics()
            while fm.horizontalAdvance(text) > max(8,w-4) and size > 5.2:
                size-=0.35; f.setPointSizeF(size); p.setFont(f); fm=p.fontMetrics()
        p.drawText(QRectF(x,y,w,max(10,size*1.7)),align,text)
    def set_document_font_size(self,size):
        self.base_font_size=max(6,min(12,int(size)))
        self.settings.setValue("documentFontSize",self.base_font_size)
        self.update()
    def center(self,p,s,x,y,w,size=9,bold=False):self.txt(p,s,x,y,w,size,bold,Qt.AlignCenter)
    def paintEvent(self,e):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing); p.scale(self.zoom,self.zoom); p.fillRect(0,0,PW,PH,Qt.white); self.draw(p); p.end()
    def draw_logo(self, p, cx, cy, scale=1.0):
        if not self.logo.isNull():
            side=int(68*scale)
            pix=self.logo.scaled(side,side,Qt.KeepAspectRatio,Qt.SmoothTransformation)
            p.drawPixmap(int(cx-pix.width()/2),int(cy-pix.height()/2),pix)

    def draw(self,p):
        p.setPen(QPen(QColor("#1d4f86"),1))
        self.draw_logo(p, 58, 45, 1.0)
        self.draw_logo(p, 736, 45, 1.0)
        self.center(p,"OFFICE ALGERIEN INTERPROFESSIONNEL DES CEREALES",80,28,635,12,True)
        self.center(p,"Coopérative de Céréales et des Légumes Secs de BATNA",80,50,635,11,True)
        self.center(p,"Bulletin d’Agréage",190,84,415,19,True)
        self.txt(p,"Espèce :",38,112,70,11,True); self.txt(p,self.data.get("espece","Blé Dur"),105,112,190,11,True)
        self.txt(p,"Date :",500,112,55,11,True); self.txt(p,self.data.get("date",""),555,112,180,11,True)
        pairs=[("Nom du producteur :","producteur",38,138,300),("Nom de l’agréeur :","agreur",500,138,255),
               ("Adresse :","adresse",38,160,300),("Quantité :","quantite",500,160,255),
               ("Point de collecte :","point",38,182,300),("N° Bon d’entrée :","bon",500,182,255)]
        for lab,k,x,y,w in pairs:self.txt(p,lab,x,y,145,9,True);self.txt(p,self.data.get(k,""),x+145,y,w-145,9)
        p.setPen(QPen(QColor("#23925f"),1));p.drawRoundedRect(QRectF(38,202,718,34),5,5)
        self.txt(p,"Résultat de l’agréage :",48,213,145,9,True); ok=self.data.get("status")=="Accepté"
        self.center(p,"◉" if ok else "○",198,213,30,12,True);self.txt(p,"Accepté",225,213,70,9,True)
        self.center(p,"○" if ok else "◉",360,213,30,12,True);self.txt(p,"Refusé",390,213,70,9,True)
        top=300; widths=[238,82,72,95,95,112]; xs=[38]
        for w in widths:xs.append(xs[-1]+w)
        heights=[34,23,23,45,58,28,23,23,23,40,23,23,23,30,30,30,28]
        rows=[("Poids spécifique (kg/hl)","[76 - 80]","poids"),("Teneur en eau (%)","≤ 17","humidite"),
              ("Ergot (%)","≤ 1","ergot"),("Matières passant au tamis 20 mm x 2.1 mm (%)","-","tamis"),
              ("Débris végétaux et éléments minéraux (%)","-","debris"),("Graines nuisibles (%)","≤ 0,25","nuisibles"),
              ("Total 1ère catégorie (%)","[1 - 3]","imp1"),("Grains cassés (%)","≤ 5","casses"),
              ("Grains fortement boutés (%)","≤ 5","boutes"),("Grains Roux (%)","-","roux"),
              ("Grains fortement mouchetés (%)","-","mouchetes"),("Grains punaisés (%)","-","punaises"),
              ("Grains piqués (%)","-","piques"),("Total 2ème catégorie (%)","≤ 10","imp2"),
              ("Grains mitadinés (%)","-","mit"),("Blé tendre dans blé dur (%)","≤ 5","tendre"),("Total mitadinés (%)","[10 - 20]","mit")]
        p.setBrush(QColor("#eef6ff"));p.drawRect(QRectF(xs[0],top,xs[-1]-xs[0],34))
        for x in xs[1:-1]:p.drawLine(x,top,x,top+34+sum(heights))
        self.center(p,"Paramètres",xs[0],top+22,widths[0],10,True);self.center(p,"Limites",xs[1],top+18,widths[1],9,True)
        self.center(p,"Valeurs",xs[2],top+22,widths[2],9,True);self.center(p,"Bonification",xs[3],top+15,widths[3],8,True)
        self.center(p,"Réfaction",xs[4],top+15,widths[4],8,True);self.center(p,"Observation",xs[5],top+22,widths[5],8,True)
        y=top+34
        for (lab,lim,key),h in zip(rows,heights):
            p.setBrush(Qt.NoBrush);p.drawRect(QRectF(xs[0],y,xs[-1]-xs[0],h))
            self.txt(p,lab,xs[0]+5,y+8,widths[0]-10,7.1,key.startswith("imp"))
            self.center(p,lim,xs[1],y+9,widths[1],7.5);self.center(p,self.values.get(key,""),xs[2],y+9,widths[2],8,True)
            b=r="0,00"
            if self.result and key in self.result[5]:
                bb,rr=self.result[5][key];b=f"{bb:+.2f}".replace(".",",");r=f"{-rr:+.2f}".replace(".",",")
            self.center(p,b,xs[3],y+9,widths[3],7.5);self.center(p,r,xs[4],y+9,widths[4],7.5);self.center(p,"-",xs[5],y+9,widths[5],7.5);y+=h
        self.center(p,"Total des Bonifications et Réfactions",xs[0],y+18,xs[2]-xs[0],9,True)
        b=r=0
        if self.result:b=self.result[0];r=self.result[1]
        self.center(p,f"+ {b:.2f}".replace(".",","),xs[3],y+18,widths[3],9,True);self.center(p,f"- {r:.2f}".replace(".",","),xs[4],y+18,widths[4],9,True)
        self.txt(p,"Référence : Décret n°88-152 du 26 juillet 1988 fixant les barèmes de bonification et de réfaction applicables aux céréales",38,y+40,718,7)
        self.txt(p,"et aux légumes secs, 1ère partie : Relations entre producteurs et organismes stockeurs.",38,y+52,718,7)
        self.txt(p,"Producteur",38,y+82,180,9,True);self.txt(p,"N° de la carte d’identité",38,y+101,210,8,True)
        self.txt(p,self.data.get("carte","................................"),225,y+101,220,8);self.txt(p,"Agréeur",580,y+82,150,9,True)
        self.txt(p,self.data.get("agreur","................................"),580,y+101,170,8)
    def set_values(self,d,v,r):self.data=d;self.values=v;self.result=r;self.update()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bulletin d’Agréage — OAIC BATNA")
        self.resize(1420, 940)
        self.setMinimumSize(1180, 760)
        self.data = {
            "espece": "Blé Dur",
            "date": datetime.date.today().strftime("%d / %m / %Y"),
            "status": "Accepté"
        }
        self.values = {k: "" for k, _, _ in QUALITY}
        self.result = None

        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(self.topbar())

        body = QWidget()
        body_lay = QHBoxLayout(body)
        body_lay.setContentsMargins(10, 10, 10, 10)
        body_lay.setSpacing(10)

        preview = QFrame()
        preview.setObjectName("previewFrame")
        pv = QVBoxLayout(preview)
        pv.setContentsMargins(6, 6, 6, 6)
        pv.setSpacing(6)

        tools = QFrame()
        tools.setObjectName("previewTools")
        tl = QHBoxLayout(tools)
        tl.setContentsMargins(6, 4, 6, 4)
        self.zoomLabel = QLabel("100%")
        self.fontSize = QComboBox()
        self.fontSize.addItems([str(i) for i in range(6,13)])
        for label, fn in [
            ("−", lambda: self.zoom(-0.1)),
            ("+", lambda: self.zoom(0.1)),
            ("Ajuster", self.fit_page),
            ("Tampons", self.toggle_stickers),
            ("Sauver position", self.save_stickers),
        ]:
            b = QPushButton(label)
            b.clicked.connect(fn)
            tl.addWidget(b)
        tl.addStretch()
        tl.addWidget(QLabel("خط"))
        tl.addWidget(self.fontSize)
        tl.addWidget(self.zoomLabel)
        pv.addWidget(tools)

        self.page = InvoicePage()
        self.fontSize.setCurrentText(str(self.page.base_font_size))
        self.fontSize.currentTextChanged.connect(lambda s: self.page.set_document_font_size(int(s)))
        self.scroll = QScrollArea()
        self.scroll.setWidget(self.page)
        self.scroll.setWidgetResizable(False)
        self.scroll.setAlignment(Qt.AlignCenter)
        pv.addWidget(self.scroll, 1)
        body_lay.addWidget(preview, 1)
        body_lay.addWidget(self.editor_panel())
        outer.addWidget(body, 1)

        outer.addWidget(self.bottom_bar())
        self.refresh()
        self.set_status("Accepté")
        self.fit_page()

    def topbar(self):
        f = QFrame()
        f.setObjectName("topbar")
        l = QHBoxLayout(f)
        l.setContentsMargins(16, 8, 16, 8)
        back = QPushButton("‹")
        back.setObjectName("back")
        back.clicked.connect(self.new_doc)
        l.addWidget(back)
        title = QLabel("Bulletin d’Agréage")
        title.setObjectName("topTitle")
        l.addWidget(title)
        sub = QLabel("Office Algérien Interprofessionnel des Céréales • BATNA")
        sub.setObjectName("topSub")
        l.addWidget(sub)
        l.addStretch()
        for txt, fn in [("Imprimer", self.export_pdf), ("Ouvrir", self.open_doc), ("⋮", self.show_menu)]:
            b = QPushButton(txt)
            b.setObjectName("topButton")
            b.clicked.connect(fn)
            l.addWidget(b)
        return f

    def show_menu(self):
        QMessageBox.information(
            self, "Bulletin d’Agréage",
            "برنامج حقيقي لملء وتحرير bulletin d’agréage.\n"
            "يمكن حفظ البيانات، حساب البونيفيكاسيون/الرفاكسيون وتصدير PDF."
        )

    def editor_panel(self):
        f = QFrame()
        f.setObjectName("editorPanel")
        f.setFixedWidth(390)
        root = QVBoxLayout(f)
        root.setContentsMargins(12, 12, 12, 12)

        title = QLabel("ملء الفاتورة")
        title.setObjectName("editorTitle")
        root.addWidget(title)

        tabs = QTabWidget()
        tabs.addTab(self.general_panel(), "البيانات")
        tabs.addTab(self.quality_panel(), "الجودة")
        root.addWidget(tabs, 1)
        return f

    def general_panel(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(2, 8, 2, 2)

        box = QGroupBox("Informations générales")
        form = QFormLayout(box)
        form.setLabelAlignment(Qt.AlignRight)
        self.gfields = {}

        combo = QComboBox()
        combo.addItems(["Blé Dur", "Blé Tendre", "Orge", "Autre"])
        self.gfields["espece"] = combo
        form.addRow("Espèce", combo)

        for k, lab in [("date", "Date")] + GENERAL:
            e = QLineEdit()
            e.setObjectName("inputField")
            e.setClearButtonEnabled(True)
            if k == "date":
                e.setInputMask("00/00/0000")
                e.setPlaceholderText("JJ/MM/AAAA")
            elif k == "quantite":
                e.setValidator(QRegularExpressionValidator(QRegularExpression(r"^[0-9]{0,7}([,.][0-9]{0,3})?$"), e))
                e.setPlaceholderText("0,000")
            self.gfields[k] = e
            form.addRow(lab, e)
            e.textChanged.connect(self.on_input_changed)
        l.addWidget(box)

        status = QGroupBox("Résultat de l’agréage")
        sl = QHBoxLayout(status)
        self.accept = QPushButton("● Accepté")
        self.reject = QPushButton("○ Refusé")
        sl.addWidget(self.accept)
        sl.addWidget(self.reject)
        l.addWidget(status)
        self.accept.clicked.connect(lambda: self.set_status("Accepté"))
        self.reject.clicked.connect(lambda: self.set_status("Refusé"))

        notes = QGroupBox("Mentions")
        nl = QVBoxLayout(notes)
        self.priceText = QTextEdit()
        self.refusalText = QTextEdit()
        self.priceText.setMaximumHeight(70)
        self.refusalText.setMaximumHeight(70)
        nl.addWidget(QLabel("Prix à débattre"))
        nl.addWidget(self.priceText)
        nl.addWidget(QLabel("Produit refusé à cause de"))
        nl.addWidget(self.refusalText)
        l.addWidget(notes)

        l.addStretch()
        return w

    def quality_panel(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(2, 8, 2, 2)
        box = QGroupBox("Valeurs mesurées")
        form = QFormLayout(box)
        form.setLabelAlignment(Qt.AlignRight)
        self.qfields = {}
        for k, lab, lim in QUALITY:
            e = QLineEdit()
            e.setObjectName("qualityInput")
            e.setValidator(QRegularExpressionValidator(QRegularExpression(r"^[0-9]{0,3}([,.][0-9]{0,2})?$"), e))
            e.setAlignment(Qt.AlignCenter)
            e.setPlaceholderText(lim)
            self.qfields[k] = e
            form.addRow(lab, e)
            e.textChanged.connect(self.on_input_changed)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(box)
        l.addWidget(scroll)
        return w

    def bottom_bar(self):
        f = QFrame()
        f.setObjectName("bottomBar")
        l = QHBoxLayout(f)
        l.setContentsMargins(12, 8, 12, 8)
        b1 = QPushButton("⚙  Paramètres")
        b2 = QPushButton("✓  Calculer")
        b3 = QPushButton("PDF  Exporter en PDF")
        b4 = QPushButton("💾  Enregistrer")
        for b, fn in [(b1, self.toggle_editor), (b2, self.calculate),
                      (b3, self.export_pdf), (b4, self.save_doc)]:
            b.clicked.connect(fn)
            l.addWidget(b)
        l.addStretch()
        return f

    def toggle_editor(self):
        w = self.centralWidget()
        if w.layout().itemAt(1) is None:
            return
        body = w.layout().itemAt(1).widget()
        if body.layout().count() > 1:
            panel = body.layout().itemAt(1).widget()
            panel.setVisible(not panel.isVisible())

    def refresh(self):
        for k, e in self.gfields.items():
            if isinstance(e, QLineEdit):
                e.setText(self.data.get(k, ""))
            else:
                e.setCurrentText(self.data.get(k, "Blé Dur"))
        for k, e in self.qfields.items():
            e.setText(self.values.get(k, ""))
        self.priceText.setPlainText(self.page.price.edit.text())
        self.refusalText.setPlainText(self.page.refusal.edit.text())
        self.page.set_values(self.data, self.values, self.result)

    def on_input_changed(self):
        if hasattr(self, "gfields") and hasattr(self, "qfields"):
            for k,e in self.gfields.items():
                self.data[k] = e.text() if isinstance(e,QLineEdit) else e.currentText()
            self.values = {k:e.text().strip() for k,e in self.qfields.items()}
            self.page.set_values(self.data,self.values,self.result)

    def collect(self):
        for k, e in self.gfields.items():
            self.data[k] = e.text() if isinstance(e, QLineEdit) else e.currentText()
        self.values = {k: e.text().strip() for k, e in self.qfields.items()}
        self.page.price.edit.setText(self.priceText.toPlainText().strip())
        self.page.refusal.edit.setText(self.refusalText.toPlainText().strip())
        self.data["status"] = "Accepté" if self.accept.property("active") else "Refusé"

    def set_status(self, s):
        self.data["status"] = s
        self.accept.setProperty("active", s == "Accepté")
        self.reject.setProperty("active", s == "Refusé")
        self.accept.setText(("●" if s == "Accepté" else "○") + "  Accepté")
        self.reject.setText(("●" if s == "Refusé" else "○") + "  Refusé")
        self.accept.style().unpolish(self.accept); self.accept.style().polish(self.accept)
        self.reject.style().unpolish(self.reject); self.reject.style().polish(self.reject)
        self.page.update()

    def calculate(self):
        self.collect()
        self.result = calculate(self.values, self.data.get("espece","Blé Dur"))
        self.page.set_values(self.data, self.values, self.result)
        self.page.price.setVisible(True)
        self.page.refusal.setVisible(True)
        self.page.save_stickers()
        self.statusBar().showMessage(
            f"Calcul terminé — Bonification +{self.result[0]:.2f} DA | "
            f"Réfaction -{self.result[1]:.2f} DA"
        )

    def new_doc(self):
        self.data = {
            "espece": "Blé Dur",
            "date": datetime.date.today().strftime("%d / %m / %Y"),
            "status": "Accepté"
        }
        self.values = {k: "" for k, _, _ in QUALITY}
        self.result = None
        self.refresh()
        self.set_status("Accepté")

    def save_doc(self):
        self.collect()
        path, _ = QFileDialog.getSaveFileName(
            self, "Enregistrer bulletin", "", "Bulletin (*.json)"
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({
                    "data": self.data,
                    "values": self.values,
                    "price": self.page.price.edit.text(),
                    "refusal": self.page.refusal.edit.text(),
                    "documentFontSize": self.page.base_font_size
                }, f, ensure_ascii=False, indent=2)
            self.statusBar().showMessage("Bulletin enregistré")

    def open_doc(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Ouvrir bulletin", "", "Bulletin (*.json)"
        )
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
            self.data = d.get("data", self.data)
            self.values = d.get("values", self.values)
            self.page.price.edit.setText(d.get("price", self.page.price.edit.text()))
            self.page.refusal.edit.setText(d.get("refusal", self.page.refusal.edit.text()))
            self.page.set_document_font_size(d.get("documentFontSize", self.page.base_font_size))
            self.fontSize.setCurrentText(str(self.page.base_font_size))
            self.refresh()
            self.set_status(self.data.get("status", "Accepté"))
            self.calculate()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def save_stickers(self):
        self.page.save_stickers()
        self.statusBar().showMessage("Positions et tailles sauvegardées")

    def toggle_stickers(self):
        self.page.price.setVisible(True)
        self.page.refusal.setVisible(True)
        self.statusBar().showMessage(
            "Déplacez les encadrés par glisser-déposer ; Ctrl + molette pour redimensionner"
        )

    def zoom(self, d):
        self.page.set_zoom(self.page.zoom + d)
        self.zoomLabel.setText(f"{int(self.page.zoom * 100)}%")

    def fit_page(self):
        vw=max(500,self.scroll.viewport().width()-24)
        vh=max(500,self.scroll.viewport().height()-24)
        z=min(1.0,vw/PW,vh/PH)
        self.page.set_zoom(z)
        self.zoomLabel.setText(f"{int(z * 100)}%")

    def export_pdf(self):
        self.calculate()
        path, _ = QFileDialog.getSaveFileName(
            self, "Exporter PDF", "", "PDF (*.pdf)"
        )
        if not path:
            return
        old = self.page.zoom
        self.page.set_zoom(1.0)
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(path)
        printer.setPageSize(QPrinter.A4)
        printer.setPageMargins(0, 0, 0, 0, QPrinter.Millimeter)
        p = QPainter(printer)
        r = printer.pageRect(QPrinter.DevicePixel)
        p.scale(r.width() / PW, r.height() / PH)
        self.page.render(p, QPoint(0, 0), self.page.rect())
        p.end()
        self.page.set_zoom(old)
        self.fit_page()
        QMessageBox.information(self, "تم التصدير", f"تم إنشاء ملف PDF:\n{path}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setLayoutDirection(Qt.LeftToRight)
    app.setStyleSheet("""
QWidget{font-family:"Segoe UI";font-size:10pt;color:#19324d}
QMainWindow{background:#e9eef5}
#topbar{background:#0d477d;min-height:58px;border-bottom:1px solid #08355e}
#back{background:transparent;border:0;color:white;font-size:30px;padding:0 10px}
#topTitle{color:white;font-size:17pt;font-weight:800;margin-left:4px}
#topSub{color:#cfe3f5;font-size:9pt;margin-left:12px}
#topButton{background:transparent;border:1px solid #6c9bc1;color:white;border-radius:7px;padding:8px 14px}
#previewFrame{background:#dce5ee;border:1px solid #cbd7e2;border-radius:8px}
#previewTools{background:white;border:1px solid #d4dee8;border-radius:7px}
#previewTools QPushButton{background:white;border:1px solid #cbd7e5;border-radius:6px;padding:6px 10px}
#editorPanel{background:white;border:1px solid #d4dee8;border-radius:8px}
#editorTitle{font-size:16pt;font-weight:800;color:#0d477d;padding:3px}
QTabWidget::pane{border:1px solid #d4dee8;border-radius:6px}
QTabBar::tab{padding:9px 18px;background:#edf3f8;border:0}
QTabBar::tab:selected{background:#0d477d;color:white}
QGroupBox{border:1px solid #d6e0ea;border-radius:8px;margin-top:10px;padding:10px;font-weight:700}
QGroupBox::title{subcontrol-origin:margin;left:10px;padding:0 5px;color:#315a7d}
QLineEdit,QTextEdit,QComboBox{border:1px solid #c7d5e2;border-radius:6px;padding:7px;background:white}
QLineEdit:focus,QTextEdit:focus,QComboBox:focus{border:2px solid #2a73a8}
#qualityInput{text-align:center;font-weight:700;min-width:70px}
#inputField{min-height:28px}
QPushButton{border:1px solid #c7d5e2;border-radius:7px;background:white;padding:8px;font-weight:600}
QPushButton[active="true"]{background:#14865a;color:white;border-color:#14865a}
#bottomBar{background:#0d477d;border-top:1px solid #08355e}
#bottomBar QPushButton{background:#16588f;color:white;border:1px solid #5b8eb7;border-radius:7px;padding:9px 16px}
QScrollArea{background:#dce5ee;border:0}
QFrame#sticker{background:#fff8d8;border:1px solid #c28b24;border-radius:8px}
QStatusBar{background:#08355e;color:white}
""")
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
