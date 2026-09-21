import sys, os, math, datetime
from PySide6.QtCore import Qt, QRectF, QPoint
from PySide6.QtGui import QPainter, QPen, QFont, QColor, QFontMetrics
from PySide6.QtWidgets import (
    QApplication, QWidget, QLineEdit, QPushButton, QLabel, QComboBox,
    QVBoxLayout, QHBoxLayout, QScrollArea, QMessageBox, QFrame
)
from PySide6.QtPrintSupport import QPrinter

DESIGN_W, DESIGN_H = 1338.0, 1900.0

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

def num(text):
    try: return float(text.replace(",", "."))
    except: return None

def tranches(exces, taille):
    return 0 if exces <= 0 else math.ceil(exces / taille)

def calculate(v):
    p, h, e = num(v("poids")), num(v("humidite")), num(v("ergot"))
    t, d, gn = num(v("tamis")) or 0, num(v("debris")) or 0, num(v("grainesNuisibles")) or 0
    c, b, r, m, pu, pi = [num(v(k)) or 0 for k in ("casses","boutes","roux","mouchetes","punaises","piques")]
    imp1, imp2 = t+d+gn, c+b+r+m+pu+pi
    mit, tender = num(v("mitadin")) or 0, num(v("bleTendre")) or 0
    mit_total = mit+tender
    bonus=refa=0.0; rows={}; notes=[]
    def add(k,bb=0,rr=0):
        nonlocal bonus,refa
        if bb or rr: rows[k]=(bb,rr)
        bonus += bb; refa += rr
    if p is not None:
        if p>80:
            add("poids", tranches(min(p,82)-80,.25)*.15 + tranches(min(p,83)-82,.25)*.10 +
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
    return bonus, refa, imp1, imp2, mit_total, rows, notes

class Sticker(QFrame):
    def __init__(self, text, refusal=False, parent=None):
        super().__init__(parent); self.refusal=refusal; self.zoom=1.0
        self.setFrameShape(QFrame.Box); self.setLineWidth(2)
        self.edit=QLineEdit(text,self); self.edit.setStyleSheet("border:0;background:transparent;")
        self.edit.setWordWrap(False)
        self.handle=QLabel("↘",self); self.handle.setAlignment(Qt.AlignCenter)
        self.handle.setStyleSheet("background:rgba(0,0,0,35);font-size:20px;")
        self.moveh=QLabel("✥",self); self.moveh.setAlignment(Qt.AlignCenter)
        self.moveh.setStyleSheet("background:rgba(0,0,0,35);font-size:18px;")
        self.drag=None; self.resize_start=None
        self.apply_style(); self.resize(360,100)
        self.moveh.mousePressEvent=self._move_press; self.moveh.mouseMoveEvent=self._move_move
        self.handle.mousePressEvent=self._resize_press; self.handle.mouseMoveEvent=self._resize_move
    def apply_style(self):
        if self.refusal:
            self.setStyleSheet("QFrame{background:#ffe8ee;border:2px solid #dc2337;border-radius:10px;} QLineEdit{color:#961423;font-size:13px;}")
        else:
            self.setStyleSheet("QFrame{background:#fff5d7;border:2px solid #be7d0f;border-radius:10px;} QLineEdit{color:#694b0a;font-size:13px;}")
    def resizeEvent(self,e):
        self.edit.setGeometry(10,8,max(1,self.width()-60),max(1,self.height()-16))
        self.moveh.setGeometry(self.width()-52,0,52,46); self.handle.setGeometry(self.width()-56,self.height()-56,56,56)
    def _move_press(self,e):
        self.drag=(e.globalPosition().toPoint(),self.pos())
    def _move_move(self,e):
        if self.drag:
            p0,pos0=self.drag; p=e.globalPosition().toPoint(); self.move(pos0+(p-p0))
    def _resize_press(self,e): self.resize_start=(e.globalPosition().toPoint(),self.zoom)
    def _resize_move(self,e):
        if self.resize_start:
            p0,z=self.resize_start; dz=(e.globalPosition().y()-p0.y())/(140*(self.parent().width()/DESIGN_W))
            self.zoom=max(.45,min(4,z+dz)); self.resize(int(360*self.zoom),int(100*self.zoom))
    def mouseReleaseEvent(self,e): self.drag=None; self.resize_start=None
    def print_mode(self,on):
        self.moveh.setVisible(not on); self.handle.setVisible(not on); self.edit.setReadOnly(on)

class BulletinCanvas(QWidget):
    def __init__(self):
        super().__init__(); self.setFixedSize(1338,1900); self.font_size=10
        self.edits={}
        for name,x,y,w,h,numeric in FIELDS:
            e=QLineEdit(self); e.setObjectName(name); e.setAlignment(Qt.AlignCenter if numeric else Qt.AlignLeft|Qt.AlignVCenter)
            e.setStyleSheet("QLineEdit{border:0;background:transparent;color:#000;padding:0 2px;}")
            e.setMaxLength(80); self.edits[name]=e
            e.setProperty("numeric",numeric)
        self.price=Sticker("PRIX À DÉBATTRE À ..........\nÀ CAUSE DE : .................................\n................................................",False,self)
        self.refusal=Sticker("PRODUIT REFUSÉ À CAUSE DE :\n................................................",True,self)
        self.price.move(690,548); self.refusal.move(690,650); self.price.hide(); self.refusal.hide()
        self.stat="Accepté"
        self.relayout()
    def set_font_size(self,s):
        self.font_size=max(6,min(14,int(s)))
        for e in self.edits.values(): e.setStyleSheet(f"QLineEdit{{border:0;background:transparent;color:#000;padding:0 2px;font-size:{self.font_size}pt;}}")
    def relayout(self):
        for name,x,y,w,h,n in FIELDS: self.edits[name].setGeometry(x,y,w,h)
    def value(self,name): return self.edits[name].text().strip()
    def draw_logo(self,p,x,y):
        p.save(); p.setPen(QPen(Qt.black,5)); p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(x+12,y+20,70,45),20*16,140*16); p.drawLine(x+22,y+62,x+70,y+62)
        p.drawLine(x+45,y+12,x+35,y+55); p.drawLine(x+45,y+12,x+57,y+55)
        p.restore()
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(),Qt.white); self.draw_page(p); p.end()
    def txt(self,p,s,x,y,size=22,bold=False,align=Qt.AlignLeft):
        f=QFont("Times New Roman",size); f.setBold(bold); p.setFont(f); p.drawText(QRectF(x,y-25,500,40),align,s)
    def centered(self,p,s,x,y,w,size=20,bold=False): self.txt(p,s,x,y,size,bold,Qt.AlignCenter)
    def draw_page(self,p):
        self.draw_logo(p,18,18); self.draw_logo(p,1230,18)
        self.centered(p,"OFFICE ALGERIEN INTERPROFESSIONNEL DES CEREALES",170,45,1000,23,True)
        self.centered(p,"Coopérative de Céréales et des Légumes Secs de BATNA",170,80,1000,21,True)
        self.centered(p,"Bulletin d’Agréage",330,125,680,32,True)
        self.txt(p,"Espèce : Blé Dur",105,180,22,True)
        for label,x,y,w in [("Date :",700,260,340),("Nom du producteur :",105,350,500),("Adresse :",105,387,500),
            ("Point de collecte :",105,424,500),("Nom de l’agréeur :",700,350,350),("Quantité :",700,387,350),("N° Bon d'entrée :",700,424,350)]:
            self.txt(p,label,x,y,20,True); p.setPen(QPen(Qt.black,1,Qt.DotLine)); p.drawLine(x+170,y+3,x+w,y+3); p.setPen(Qt.black)
        x0,x1,x2,x3,x4,x5,x6=102,530,653,760,927,1063,1155
        ys=[530,638,670,710,753,828,937,1005,1047,1084,1135,1184,1235,1274,1317,1367,1417,1471,1515,1576,1618]
        p.setPen(QPen(Qt.black,1.4)); p.drawRect(QRectF(x0,ys[0],x6-x0,ys[-1]-ys[0]))
        for y in ys[1:-1]: p.drawLine(x0,y,x6,y)
        for x in [x1,x2,x3,x4,x5]: p.drawLine(x,ys[0],x,ys[-1])
        self.centered(p,"Paramètres",x0,575,x1-x0,24,True); self.centered(p,"Limites",x1,557,x2-x1,23,True)
        self.centered(p,"(sans",x1,582,x2-x1,14,True); self.centered(p,"bonification ni",x1,599,x2-x1,14,True); self.centered(p,"réfaction)",x1,616,x2-x1,14,True)
        self.centered(p,"Valeurs",x2,575,x3-x2,23,True); self.centered(p,"Bonification",x3,560,x4-x3,21,True); self.centered(p,"(D.A.)",x3,585,x4-x3,19,True)
        self.centered(p,"Réfaction",x4,560,x5-x4,21,True); self.centered(p,"(D.A.)",x4,585,x5-x4,19,True); self.centered(p,"Observation",x5,575,x6-x5,20,True)
        rows=[(638,670,"Poids spécifique (kg/hl)","[76 - 80]"),(670,710,"Teneur en eau (%)","≤ 17"),(710,753,"Ergot (‰)","≤ 1"),
        (937,1005,"Graines nuisibles (%)","≤ 0,25"),(1047,1084,"Grains cassés (%)","≤ 5"),(1084,1135,"Grains fortement boutés (%)","≤ 5"),
        (1135,1184,"Grains Roux (%)","-"),(1274,1317,"Grains punaisés (%)","-"),(1317,1367,"Grains piqués (%)","-")]
        for top,bot,label,lim in rows: self.txt(p,label,145,(top+bot)/2+7,19,True); self.centered(p,lim,530,(top+bot)/2+7,123,20,True)
        self.txt(p,"Matières qui passent à travers\nle tamis 20 mm x2.1mm (%)",145,790,18,True)
        self.txt(p,"Les débris végétaux et les\néléments minéraux (%)",145,870,18,True)
        self.txt(p,"Total (%)",145,1032,19,True); self.centered(p,"[1 - 3]",530,1032,123,20,True)
        self.txt(p,"Grains fortement mouchetés (%)",145,1260,18,True)
        self.txt(p,"Total (%)",145,1392,19,True); self.centered(p,"≤ 10",530,1392,123,20,True)
        self.txt(p,"Grains mitadinés (%)",145,1450,19,True); self.centered(p,"-",530,1450,123,20,True)
        self.txt(p,"Blé tendre dans blé dur (%)",145,1498,19,True); self.centered(p,"≤ 5",530,1498,123,20,True)
        self.txt(p,"Total (%)",145,1548,19,True); self.centered(p,"[10 - 20]",530,1548,123,20,True)
        self.centered(p,"Impuretés 1ère catégorie",316,875,210,19,True); self.centered(p,"Impuretés 2ème catégorie",316,1200,210,19,True)
        self.centered(p,"Grains mitadinés",316,1490,210,19,True)
        self.txt(p,"Total des Bonifications et Réfactions",102,1605,20,True)
        self.txt(p,"Référence : Décret n°88-152 du 26 juillet 1988",104,1660,15); self.txt(p,"Producteur",105,1740,22,True); self.txt(p,"N° de la carte d’identité",105,1800,21,True); self.txt(p,"Agréeur",1030,1740,22,True)
    def update_results(self, result):
        bonus,refa,imp1,imp2,mit,rows,notes=result
        self.edits["impur1Total"].setText(f"{imp1:.2f}"); self.edits["impur2Total"].setText(f"{imp2:.2f}"); self.edits["mitadinTotal"].setText(f"{mit:.2f}")
        self.update()
        return result

class MainWindow(QWidget):
    def __init__(self):
        super().__init__(); self.setWindowTitle("Bulletin d’Agréage — Windows"); self.resize(1250,900)
        self.canvas=BulletinCanvas(); self.font=10
        scroll=QScrollArea(); scroll.setWidget(self.canvas); scroll.setWidgetResizable(False); scroll.setAlignment(Qt.AlignCenter)
        controls=QHBoxLayout()
        calc=QPushButton("حساب"); pdf=QPushButton("تصدير PDF"); minus=QPushButton("−"); plus=QPushButton("+"); reset=QPushButton("افتراضي")
        self.fontLabel=QLabel("حجم الخط: 10"); self.status=QComboBox(); self.status.addItems(["قابل للاستلام","مرفوض"]); self.result=QLabel("")
        minus.clicked.connect(lambda:self.set_font(self.font-1)); plus.clicked.connect(lambda:self.set_font(self.font+1)); reset.clicked.connect(lambda:self.set_font(10))
        calc.clicked.connect(self.do_calc); pdf.clicked.connect(self.export_pdf); self.status.currentIndexChanged.connect(self.status_changed)
        for w in [calc,pdf,minus,self.fontLabel,plus,reset,self.status]: controls.addWidget(w)
        root=QVBoxLayout(self); root.addLayout(controls); root.addWidget(scroll); root.addWidget(self.result)
        self.status_changed(0)
    def set_font(self,s):
        self.font=max(6,min(14,s)); self.canvas.set_font_size(self.font); self.fontLabel.setText(f"حجم الخط: {self.font}")
    def status_changed(self,i):
        self.canvas.refusal.setVisible(i==1); self.canvas.update()
    def do_calc(self):
        r=self.canvas.update_results(calculate(self.canvas.value))
        bonus,refa,imp1,imp2,mit,rows,notes=r
        self.canvas.price.setVisible(imp1>6 or imp2>20)
        lines=[f"BONIFICATION : {bonus:.2f} DA",f"RÉFACTION : {refa:.2f} DA",f"SOLDE : {bonus-refa:.2f} DA",
               f"Impuretés 1ère catégorie : {imp1:.2f} %",f"Impuretés 2ème catégorie : {imp2:.2f} %",
               f"Total mitadin + blé tendre : {mit:.2f} %"]+["• "+n for n in notes]
        self.result.setText("\n".join(lines))
    def export_pdf(self):
        self.do_calc(); path=os.path.join(os.path.expanduser("~"),"Downloads",f"Bulletin_Agreage_{datetime.datetime.now():%Y%m%d_%H%M%S}.pdf")
        os.makedirs(os.path.dirname(path),exist_ok=True)
        self.canvas.price.print_mode(True); self.canvas.refusal.print_mode(True)
        printer=QPrinter(QPrinter.HighResolution); printer.setOutputFormat(QPrinter.PdfFormat); printer.setOutputFileName(path); printer.setPageSize(QPrinter.A4); printer.setPageMargins(0,0,0,0,QPrinter.Millimeter)
        painter=QPainter(printer); target=QRectF(0,0,printer.pageRect(QPrinter.DevicePixel).width(),printer.pageRect(QPrinter.DevicePixel).height())
        painter.save(); painter.scale(target.width()/DESIGN_W,target.height()/DESIGN_H); self.canvas.render(painter,QPoint(0,0),QRect(0,0,int(DESIGN_W),int(DESIGN_H))); painter.restore(); painter.end()
        self.canvas.price.print_mode(False); self.canvas.refusal.print_mode(False)
        QMessageBox.information(self,"تم","تم حفظ PDF في مجلد Downloads:\n"+path)

if __name__=="__main__":
    app=QApplication(sys.argv); app.setLayoutDirection(Qt.RightToLeft); w=MainWindow(); w.show(); sys.exit(app.exec())
