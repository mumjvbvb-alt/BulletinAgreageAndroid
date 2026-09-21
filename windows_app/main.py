import sys, os, json, math, datetime
from PySide6.QtCore import Qt, QRectF, QPoint, QSettings
from PySide6.QtGui import QPainter, QPen, QFont, QColor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel, QLineEdit, QComboBox,
    QPushButton, QVBoxLayout, QHBoxLayout, QFormLayout, QScrollArea,
    QGroupBox, QFileDialog, QMessageBox, QSplitter
)
from PySide6.QtPrintSupport import QPrinter

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

def calculate(q):
    p,h,e=fnum(q.get("poids")),fnum(q.get("humidite")),fnum(q.get("ergot"))
    v={k:(fnum(q.get(k)) or 0) for k,_,_ in QUALITY}
    i1=v["tamis"]+v["debris"]+v["nuisibles"]
    i2=v["casses"]+v["boutes"]+v["roux"]+v["mouchetes"]+v["punaises"]+v["piques"]
    mit=v["mitadin"]+v["tendre"]; bonus=red=0.; rows={}; notes=[]
    def add(k,b=0,r=0):
        nonlocal bonus,red
        bonus+=b; red+=r; rows[k]=(b,r)
    if p is not None:
        if p>80:add("poids",steps(p-80,.25)*.15)
        elif p>=72:add("poids",r=steps(76-p,.25)*.10)
        else:notes.append("Poids spécifique inférieur à 72 kg/hl : hors limite.")
    if h is not None and h>17:notes.append("Humidité supérieure à 17 % : hors limite.")
    if e is not None and e>1:add("ergot",r=steps(e-1,.25)*.50)
    if i1<1:add("imp1",b=steps(1-i1,.25)*.125)
    elif 3<i1<=6:add("imp1",r=steps(i1-3,.25)*.125)
    elif i1>6:notes.append("Impuretés 1ère catégorie > 6 % : prix à débattre.")
    if v["casses"]>5:add("casses",r=steps(v["casses"]-5,.25)*.075)
    if v["boutes"]>5:add("boutes",r=steps(v["boutes"]-5,1)*.05)
    if 10<i2<=20:add("imp2",r=steps(i2-10,1)*.50)
    elif i2>20:notes.append("Impuretés 2ème catégorie > 20 % : hors barème.")
    if 20<mit<=70:add("mit",r=steps(mit-20,1)*.05)
    elif mit>70:notes.append("Mitadin + blé tendre > 70 % : situation à traiter selon le barème.")
    if v["tendre"]>10:notes.append("Blé tendre > 10 % : mention spéciale.")
    return bonus,red,i1,i2,mit,rows,notes

class Sticker(QFrame):
    def __init__(self,title,text,accent,parent):
        super().__init__(parent); self.drag=None; self.accent=accent
        lay=QVBoxLayout(self); lay.setContentsMargins(10,6,10,6)
        self.title=QLabel(title); self.title.setStyleSheet(f"color:{accent};font-weight:800")
        self.edit=QLineEdit(text); self.edit.setStyleSheet("border:0;background:transparent;font-weight:700")
        lay.addWidget(self.title); lay.addWidget(self.edit); self.resize(285,72)
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
        self.setMinimumSize(PW,PH)
        self.price=Sticker("PRIX À DÉBATTRE","PRIX À DÉBATTRE À .......... — À CAUSE DE : ................","#a76b00",self)
        self.refusal=Sticker("PRODUIT REFUSÉ À CAUSE DE","........................................................","#c51f3a",self)
        self.load_stickers()
    def load_stickers(self):
        for s,k,d in [(self.price,"price",QPoint(42,315)),(self.refusal,"refusal",QPoint(405,315))]:
            s.setGeometry(self.settings.value(k+"X",d.x(),int),self.settings.value(k+"Y",d.y(),int),
                          self.settings.value(k+"W",285,int),self.settings.value(k+"H",72,int))
            s.edit.setText(self.settings.value(k+"Text",s.edit.text()))
        self.price.hide(); self.refusal.hide()
    def save_stickers(self):
        for s,k in [(self.price,"price"),(self.refusal,"refusal")]:
            for n,v in [("X",s.x()),("Y",s.y()),("W",s.width()),("H",s.height()),("Text",s.edit.text())]:
                self.settings.setValue(k+n,v)
    def set_zoom(self,z):
        self.zoom=max(.5,min(1.4,z)); self.setFixedSize(int(PW*self.zoom),int(PH*self.zoom)); self.update()
    def txt(self,p,s,x,y,w=200,size=9,bold=False,align=Qt.AlignLeft):
        f=QFont("Times New Roman",size); f.setBold(bold); p.setFont(f); p.drawText(QRectF(x,y,w,size*1.7),align,s)
    def center(self,p,s,x,y,w,size=9,bold=False):self.txt(p,s,x,y,w,size,bold,Qt.AlignCenter)
    def paintEvent(self,e):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing); p.scale(self.zoom,self.zoom); p.fillRect(0,0,PW,PH,Qt.white); self.draw(p); p.end()
    def draw(self,p):
        p.setPen(QPen(QColor("#1d4f86"),1))
        self.center(p,"◈",25,35,45,28,True); self.center(p,"◈",724,35,45,28,True)
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
        top=255; widths=[238,82,72,95,95,112]; xs=[38]
        for w in widths:xs.append(xs[-1]+w)
        heights=[34,23,23,45,58,28,23,23,23,40,23,23,23,30,30,30,28]
        rows=[("Poids spécifique (kg/hl)","[76 - 80]","poids"),("Teneur en eau (%)","≤ 17","humidite"),
              ("Ergot (%)","≤ 1","ergot"),("Matières passant au tamis 20 mm x 2.1mm (%)","-","tamis"),
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
        super().__init__();self.setWindowTitle("Bulletin d’Agréage");self.resize(1500,920);self.setMinimumSize(1200,760)
        self.data={"espece":"Blé Dur","date":datetime.date.today().strftime("%d / %m / %Y"),"status":"Accepté"};self.values={k:"" for k,_,_ in QUALITY};self.result=None
        root=QWidget();self.setCentralWidget(root);outer=QHBoxLayout(root);outer.setContentsMargins(0,0,0,0);outer.setSpacing(0)
        outer.addWidget(self.nav());center=QWidget();cv=QVBoxLayout(center);cv.setContentsMargins(8,8,8,8);cv.addWidget(self.toolbar())
        self.page=InvoicePage();self.scroll=QScrollArea();self.scroll.setWidget(self.page);self.scroll.setWidgetResizable(False);self.scroll.setAlignment(Qt.AlignCenter);cv.addWidget(self.scroll,1);outer.addWidget(center,1);outer.addWidget(self.panel());self.refresh();self.fit_page()
    def nav(self):
        f=QFrame();f.setObjectName("nav");f.setFixedWidth(NAV_W);l=QVBoxLayout(f);l.setContentsMargins(12,18,12,18)
        b=QLabel("◈  Bulletin d’Agréage");b.setObjectName("brand");l.addWidget(b)
        for t,fn in [("⌂  Accueil",self.new_doc),("＋  Nouveau",self.new_doc),("▣  Ouvrir",self.open_doc),("▣  Enregistrer",self.save_doc),("▣  Exporter PDF",self.export_pdf),("⚙  Paramètres",lambda:None)]:
            q=QPushButton(t);q.setObjectName("navbtn");q.clicked.connect(fn);l.addWidget(q)
        l.addStretch();l.addWidget(QLabel("O.A.I.C\nBATNA",objectName="navfoot"));return f
    def toolbar(self):
        f=QFrame();f.setObjectName("toolbar");l=QHBoxLayout(f);l.setContentsMargins(8,6,8,6)
        for t,fn in [("−",lambda:self.zoom(-.1)),("+",lambda:self.zoom(.1)),("Ajuster",self.fit_page),("Modifier les tampons",self.toggle_stickers),("Sauvegarder position",self.save_stickers)]:
            q=QPushButton(t);q.clicked.connect(fn);l.addWidget(q)
        l.addStretch();self.zoomLabel=QLabel("100%");l.addWidget(self.zoomLabel);return f
    def panel(self):
        f=QFrame();f.setObjectName("panel");f.setFixedWidth(PANEL_W);root=QVBoxLayout(f);root.setContentsMargins(12,12,12,12)
        t=QLabel("Saisie des données");t.setObjectName("paneltitle");root.addWidget(t)
        tabs=QHBoxLayout();a=QPushButton("Données générales");b=QPushButton("Paramètres qualité");tabs.addWidget(a);tabs.addWidget(b);root.addLayout(tabs)
        self.stack=QStackedWidget();root.addWidget(self.stack,1);self.stack.addWidget(self.general_panel());self.stack.addWidget(self.quality_panel());a.clicked.connect(lambda:self.stack.setCurrentIndex(0));b.clicked.connect(lambda:self.stack.setCurrentIndex(1));return f
    def general_panel(self):
        w=QWidget();l=QVBoxLayout(w);box=QGroupBox("Informations générales");form=QFormLayout(box);self.gfields={}
        self.gfields["espece"]=QComboBox();self.gfields["espece"].addItems(["Blé Dur","Blé Tendre","Orge","Autre"]);form.addRow("Espèce",self.gfields["espece"])
        for k,lab in [("date","Date")]+GENERAL:e=QLineEdit();self.gfields[k]=e;form.addRow(lab,e)
        l.addWidget(box);s=QGroupBox("Résultat de l’agréage");sl=QHBoxLayout(s);self.accept=QPushButton("◉  Accepté");self.reject=QPushButton("○  Refusé");sl.addWidget(self.accept);sl.addWidget(self.reject);l.addWidget(s)
        self.accept.clicked.connect(lambda:self.set_status("Accepté"));self.reject.clicked.connect(lambda:self.set_status("Refusé"))
        n=QGroupBox("Notes / Mentions");nl=QVBoxLayout(n);self.priceText=QLineEdit();self.refusalText=QLineEdit();nl.addWidget(QLabel("PRIX À DÉBATTRE"));nl.addWidget(self.priceText);nl.addWidget(QLabel("PRODUIT REFUSÉ À CAUSE DE"));nl.addWidget(self.refusalText);l.addWidget(n)
        self.calc=QPushButton("Calculer les résultats");self.calc.setObjectName("primary");self.pdf=QPushButton("Exporter en PDF");self.pdf.setObjectName("pdf");l.addWidget(self.calc);l.addWidget(self.pdf);self.calc.clicked.connect(self.calculate);self.pdf.clicked.connect(self.export_pdf);l.addStretch();return w
    def quality_panel(self):
        w=QWidget();l=QVBoxLayout(w);box=QGroupBox("Valeurs mesurées");form=QFormLayout(box);self.qfields={}
        for k,lab,_ in QUALITY:e=QLineEdit();e.setPlaceholderText("Valeur");self.qfields[k]=e;form.addRow(lab,e)
        l.addWidget(box);l.addStretch();return w
    def refresh(self):
        for k,e in self.gfields.items():
            e.setText(self.data.get(k,"")) if isinstance(e,QLineEdit) else e.setCurrentText(self.data.get(k,"Blé Dur"))
        for k,e in self.qfields.items():e.setText(self.values.get(k,""))
        self.priceText.setText(self.page.price.edit.text());self.refusalText.setText(self.page.refusal.edit.text());self.page.set_values(self.data,self.values,self.result)
    def collect(self):
        for k,e in self.gfields.items():self.data[k]=e.text() if isinstance(e,QLineEdit) else e.currentText()
        self.values={k:e.text().strip() for k,e in self.qfields.items()};self.page.price.edit.setText(self.priceText.text());self.page.refusal.edit.setText(self.refusalText.text());self.data["status"]="Accepté" if self.accept.property("active") else "Refusé"
    def set_status(self,s):
        self.data["status"]=s;self.accept.setProperty("active",s=="Accepté");self.reject.setProperty("active",s=="Refusé")
        self.accept.setText(("◉" if s=="Accepté" else "○")+"  Accepté");self.reject.setText(("◉" if s=="Refusé" else "○")+"  Refusé");self.page.update()
    def calculate(self):
        self.collect();self.result=calculate(self.values);self.page.set_values(self.data,self.values,self.result)
        self.page.price.setVisible(self.result[2]>6);self.page.refusal.setVisible(self.data["status"]=="Refusé");self.page.save_stickers()
        self.statusBar().showMessage(f"Calcul terminé — Bonification +{self.result[0]:.2f} DA | Réfaction -{self.result[1]:.2f} DA")
    def new_doc(self):
        self.data={"espece":"Blé Dur","date":datetime.date.today().strftime("%d / %m / %Y"),"status":"Accepté"};self.values={k:"" for k,_,_ in QUALITY};self.result=None;self.refresh();self.set_status("Accepté")
    def save_doc(self):
        self.collect();path,_=QFileDialog.getSaveFileName(self,"Enregistrer bulletin","","Bulletin (*.json)")
        if path:
            with open(path,"w",encoding="utf-8") as f:json.dump({"data":self.data,"values":self.values,"price":self.page.price.edit.text(),"refusal":self.page.refusal.edit.text()},f,ensure_ascii=False,indent=2)
            self.statusBar().showMessage("Bulletin enregistré")
    def open_doc(self):
        path,_=QFileDialog.getOpenFileName(self,"Ouvrir bulletin","","Bulletin (*.json)")
        if not path:return
        try:
            with open(path,encoding="utf-8") as f:d=json.load(f)
            self.data=d.get("data",self.data);self.values=d.get("values",self.values);self.page.price.edit.setText(d.get("price",self.page.price.edit.text()));self.page.refusal.edit.setText(d.get("refusal",self.page.refusal.edit.text()));self.refresh();self.set_status(self.data.get("status","Accepté"));self.calculate()
        except Exception as e:QMessageBox.critical(self,"Erreur",str(e))
    def save_stickers(self):self.page.save_stickers();self.statusBar().showMessage("Positions et tailles sauvegardées")
    def toggle_stickers(self):
        self.page.price.setVisible(True);self.page.refusal.setVisible(True);self.statusBar().showMessage("Déplacez les tampons par glisser-déposer ; Ctrl + molette pour redimensionner")
    def zoom(self,d):self.page.set_zoom(self.page.zoom+d);self.zoomLabel.setText(f"{int(self.page.zoom*100)}%")
    def fit_page(self):
        h=max(500,self.scroll.viewport().height()-20);z=min(1.,h/PH);self.page.set_zoom(z);self.zoomLabel.setText(f"{int(z*100)}%")
    def export_pdf(self):
        self.calculate();path,_=QFileDialog.getSaveFileName(self,"Exporter PDF","","PDF (*.pdf)")
        if not path:return
        old=self.page.zoom;self.page.set_zoom(1.);printer=QPrinter(QPrinter.HighResolution);printer.setOutputFormat(QPrinter.PdfFormat);printer.setOutputFileName(path);printer.setPageSize(QPrinter.A4);printer.setPageMargins(0,0,0,0,QPrinter.Millimeter)
        p=QPainter(printer);r=printer.pageRect(QPrinter.DevicePixel);p.scale(r.width()/PW,r.height()/PH);self.page.render(p,QPoint(0,0),self.page.rect());p.end();self.page.set_zoom(old);self.fit_page();QMessageBox.information(self,"تم التصدير",f"تم إنشاء ملف PDF:\n{path}")

if __name__=="__main__":
    app=QApplication(sys.argv);app.setStyle("Fusion");app.setLayoutDirection(Qt.LeftToRight)
    app.setStyleSheet('''
QWidget{font-family:"Segoe UI";font-size:10pt;color:#172b4d}QMainWindow{background:#edf2f7}
#nav{background:#0e3764}#brand{color:white;font-size:16pt;font-weight:800;padding:10px}
#navbtn{color:white;background:transparent;border:0;border-radius:7px;text-align:left;padding:12px;font-weight:600}#navbtn:hover{background:#174b82}
#navfoot{color:#b9d2eb;background:#0a2b50;border-radius:8px;padding:16px;text-align:center}
#toolbar,#panel{background:white;border:1px solid #d8e1eb;border-radius:8px}#toolbar QPushButton{border:1px solid #d3dce7;background:#fff;padding:8px 12px;border-radius:7px}
#panel{border-radius:0;border-top:0;border-bottom:0}#paneltitle{font-size:17pt;font-weight:800;color:#123e70;padding:6px}
QGroupBox{border:1px solid #d8e1eb;border-radius:9px;margin-top:10px;padding:10px;font-weight:700}QGroupBox::title{subcontrol-origin:margin;left:10px;padding:0 5px;color:#365a7d}
QLineEdit,QComboBox{border:1px solid #cbd7e5;border-radius:6px;padding:7px;background:#fff}QPushButton{border:1px solid #cbd7e5;border-radius:7px;background:#fff;padding:8px;font-weight:600}
QPushButton#primary{background:#0878d1;color:#fff;border:0}QPushButton#pdf{background:#173f70;color:#fff;border:0}
QScrollArea{background:#dfe7ef;border:0}QFrame#sticker{background:#fff8dc;border:1px solid #c58b22;border-radius:8px}QStatusBar{background:#0e3764;color:#fff}
''')
    w=MainWindow();w.show();sys.exit(app.exec())
