from io import BytesIO
from pathlib import Path
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QPen, QFont, QImage, QPixmap
from PySide6.QtWidgets import QWidget, QLineEdit
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from logo_data import logo_image
from invoice_engine import RULES, fmt

W,H=1338,1900
COLS=(102,530,653,760,927,1063,1235)

HEADER_FIELDS={
 "date":(805,246,225,32),"producer":(380,336,155,32),"address":(250,373,285,32),
 "point":(340,410,195,32),"agreer":(940,336,110,32),"quantity":(835,373,175,32),
 "bon":(885,410,165,32),"producer_id":(110,1778,360,38)
}

def rows_for(species):
    if species=="Blé Dur":
        return [
        ("poids","Poids spécifique (kg/hl)","76 – 80"),("humidite","Teneur en eau (%)","≤ 17"),
        ("ergot","Ergot (‰)","≤ 1"),("tamis","Matières au tamis (%)","—"),
        ("debris","Débris végétaux et minéraux (%)","—"),("graines_nuisibles","Graines nuisibles (%)","≤ 0,25"),
        ("impur1","Impuretés 1ère catégorie (%)","1 – 3"),("casses","Grains cassés (%)","≤ 5"),
        ("boutes","Grains fortement boutés (%)","≤ 5"),("roux","Grains roux (%)","—"),
        ("mouchetes","Grains fortement mouchetés (%)","—"),("punaises","Grains punaisés (%)","—"),
        ("piques","Grains piqués (%)","—"),("impur2","Impuretés 2ème catégorie (%)","≤ 10"),
        ("mitadin","Grains mitadinés (%)","10 – 20"),("ble_tendre","Blé tendre dans blé dur (%)","≤ 5"),
        ("mitadin_total","Total mitadin (%)","10 – 20")]
    if species=="Blé Tendre":
        return [("poids","Poids spécifique (kg/hl)","74 – 77"),("humidite","Teneur en eau (%)","≤ 17"),
        ("ergot","Ergot (‰)","≤ 1"),("impur1","Impuretés 1ère catégorie (%)","1 – 3"),
        ("casses","Grains cassés (%)","≤ 4"),("boutes","Grains boutés (%)","≤ 5"),
        ("punaises","Grains punaisés (%)","≤ 2"),("impur2","Impuretés 2ème catégorie (%)","≤ 6")]
    return [("poids","Poids spécifique (kg/hl)","58 – 62"),("humidite","Teneur en eau (%)","≤ 17"),
    ("impurites","Impuretés diverses (%)","≤ 2"),("ergot","Ergot (‰)","≤ 1")]

class InvoicePreview(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent); self.species="Blé Dur"; self.data={}; self.result=None
        self.layout_map={}; self.edit_mode=False; self.selected=None; self.edits={}
        self.fields={}; self.setMinimumSize(500,700); self.setStyleSheet("background:white;")
    def set_data(self,data,result):
        self.data=data; self.result=result; self.species=data.get("species","Blé Dur")
        self.rebuild_fields(); self.update()
    def rebuild_fields(self):
        for w in list(self.fields.values()): w.deleteLater()
        self.fields={}
        defaults=dict(HEADER_FIELDS)
        y=638
        for key,_,_ in rows_for(self.species):
            defaults[key]=(655,y+4,105,30); y+=40
        for key,(x,y,w,h) in defaults.items():
            conf=self.edits.get(key,{})
            self.layout_map[key]=(conf.get("x",x),conf.get("y",y),conf.get("font",10),w,h)
            e=QLineEdit(self)
            e.setText(str(self.data.get("values",{}).get(key,"") if key not in HEADER_FIELDS else self.data.get(key,"")))
            e.setFrame(False); e.setAlignment(Qt.AlignCenter if key not in HEADER_FIELDS else Qt.AlignLeft|Qt.AlignVCenter)
            e.setStyleSheet("background:transparent;color:#000;border:none;")
            e.setFont(QFont("Times New Roman",self.layout_map[key][2]))
            e.textChanged.connect(lambda _,k=key:self._changed(k))
            self.fields[key]=e
        self.relayout()
    def _changed(self,key):
        if key in HEADER_FIELDS:self.data[key]=self.fields[key].text()
        else:self.data.setdefault("values",{})[key]=self.fields[key].text()
        self.update()
    def relayout(self):
        s=min(self.width()/W,self.height()/H); ox=(self.width()-W*s)/2; oy=(self.height()-H*s)/2
        for k,e in self.fields.items():
            x,y,f,w,h=self.layout_map[k]; e.setGeometry(int(ox+x*s),int(oy+y*s),max(2,int(w*s)),max(2,int(h*s)))
            e.setFont(QFont("Times New Roman",max(6,int(f*s))))
            e.setVisible(True)
    def resizeEvent(self,e): self.relayout(); super().resizeEvent(e)
    def set_edit_mode(self,on):
        self.edit_mode=on
        for e in self.fields.values(): e.setReadOnly(on and False)
        self.update()
    def set_layout(self,key,x,y,font):
        if key not in self.layout_map:return
        _,_,_,w,h=self.layout_map[key]; self.layout_map[key]=(x,y,font,w,h)
        self.edits[key]={"x":x,"y":y,"font":font}; self.relayout(); self.update()
    def reset_layout(self):
        self.edits={}; self.rebuild_fields()
    def layout_json(self): return self.edits
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing); s=min(self.width()/W,self.height()/H); ox=(self.width()-W*s)/2; oy=(self.height()-H*s)/2
        p.translate(ox,oy); p.scale(s,s); self.draw_page(p); p.end()
    def draw_page(self,p):
        p.fillRect(0,0,W,H,Qt.white); pen=QPen(Qt.black,1.3); p.setPen(pen)
        # logo
        try:
            im=logo_image(); raw=BytesIO(); im.save(raw,format="PNG"); q=QImage.fromData(raw.getvalue()); p.drawImage(QRectF(22,18,100,100),q)
            p.drawImage(QRectF(W-122,18,100,100),q)
        except Exception: pass
        def txt(t,x,y,size,bold=False,align=Qt.AlignLeft):
            f=QFont("Times New Roman",size); f.setBold(bold); p.setFont(f); p.drawText(QRectF(x,y-28,300,35),align,t)
        txt("OFFICE ALGERIEN INTERPROFESSIONNEL DES CEREALES",115,78,28,True,Qt.AlignCenter)
        txt("Coopérative de Céréales et des Légumes Secs de BATNA",170,142,24,True,Qt.AlignCenter)
        txt("Bulletin d'Agréage",330,205,34,False,Qt.AlignCenter)
        txt("Espèce :",104,270,23,True); txt(self.species,235,270,27,False)
        txt("Date :",700,270,23,True); txt("Nom du producteur :",104,360,20,True); txt("Adresse :",104,397,20,True)
        txt("Point de collecte :",104,434,20,True); txt("Nom de l'agréeur :",700,360,20,True)
        txt("Quantité :",700,397,20,True); txt("N° Bon d'entrée :",700,434,20,True)
        self.draw_table(p,txt)
        txt("Référence : Décret n°88-152 du 26 juillet 1988 fixant les barèmes de bonification et de réfaction",104,1660,14)
        txt("applicables aux céréales et aux légumes secs.",104,1682,14)
        txt("Producteur",105,1740,20,True); txt("N° de la carte d’identité",105,1800,19,True); txt("Agréeur",1030,1740,20,True,Qt.AlignCenter)
        status=self.data.get("status","ACCEPTED")
        if status=="REFUSED":
            self.notice(p,"PRODUIT REFUSÉ À CAUSE DE :",self.data.get("reason",""),690,548)
        elif self.result and self.result.price_to_discuss:
            self.notice(p,"PRIX À DÉBATTRE À CAUSE DE :",self.result.observation,690,548)
    def draw_table(self,p,txt):
        x0,x1,x2,x3,x4,x5,x6=COLS; top=530; rows=rows_for(self.species); rh=62 if len(rows)<10 else 55
        bottom=top+82+len(rows)*rh+50
        p.drawRect(x0,top,x6-x0,bottom-top)
        for x in COLS[1:-1]:p.drawLine(x,top,x,bottom)
        p.drawLine(x0,612,x6,612)
        txt("Paramètres",x0,575,22,True,Qt.AlignCenter); txt("Limites",x1,575,20,True,Qt.AlignCenter); txt("Valeurs",x2,575,20,True,Qt.AlignCenter)
        txt("Bonification",x3,560,18,True,Qt.AlignCenter); txt("(D.A.)",x3,584,16,True,Qt.AlignCenter)
        txt("Réfaction",x4,560,18,True,Qt.AlignCenter); txt("(D.A.)",x4,584,16,True,Qt.AlignCenter); txt("Observation",x5,575,17,True,Qt.AlignCenter)
        for i,(key,label,lim) in enumerate(rows):
            y=612+i*rh; p.drawLine(x0,y+rh,x6,y+rh); txt(label,120,y+rh/2+7,15,True)
            txt(lim,x1,y+rh/2+7,15,True,Qt.AlignCenter)
            if self.result:
                b,rf=self.result.rows.get(key,(0,0))
                if b: txt(fmt(b),x3,y+rh/2+7,14,True,Qt.AlignCenter)
                if rf: txt(fmt(rf),x4,y+rh/2+7,14,True,Qt.AlignCenter)
        y=bottom-25; txt("Total des Bonifications et Réfactions",x0,y,16,True,Qt.AlignCenter)
        if self.result:
            txt(fmt(self.result.bonus),x3,y,16,True,Qt.AlignCenter); txt(fmt(self.result.refaction),x4,y,16,True,Qt.AlignCenter)
            txt((self.result.observation or "")[:20],x5,y,11,False,Qt.AlignCenter)
    def notice(self,p,title,reason,x,y):
        p.setPen(QPen(Qt.black,2)); p.drawRect(x,y,480,105); 
        f=QFont("Times New Roman",17); f.setBold(True); p.setFont(f); p.drawText(QRectF(x+12,y+8,456,30),title)
        f.setPointSize(13); f.setBold(False); p.setFont(f); p.drawText(QRectF(x+12,y+42,456,55),Qt.TextWordWrap,reason or "................................................")
    def pdf(self,path):
        c=canvas.Canvas(str(path),pagesize=A4); sx=A4[0]/W; sy=A4[1]/H
        c.saveState(); c.scale(sx,sy); c.setLineWidth(0.8); c.setFont("Times-Roman",12)
        self._pdf_page(c); c.restoreState(); c.save()
    def _pdf_page(self,c):
        c.setFillColorRGB(1,1,1); c.rect(0,0,W,H,fill=1,stroke=0); c.setFillColorRGB(0,0,0)
        try:
            im=logo_image(); bio=BytesIO(); im.save(bio,format="PNG"); bio.seek(0)
            c.drawImage(ImageReader(bio),22,H-118,100,100,mask="auto"); c.drawImage(ImageReader(bio),W-122,H-118,100,100,mask="auto")
        except Exception: pass
        def t(s,x,y,size=12,b=False,center=False):
            c.setFont("Times-Bold" if b else "Times-Roman",size); c.drawCentredString(x,y,size and s) if False else (c.drawCentredString(x,y,s) if center else c.drawString(x,y,s))
        t("OFFICE ALGERIEN INTERPROFESSIONNEL DES CEREALES",669,1822,28,True,True)
        t("Coopérative de Céréales et des Légumes Secs de BATNA",669,1758,24,True,True)
        t("Bulletin d'Agréage",669,1695,34,False,True); t("Espèce :",104,1630,23,True); t(self.species,235,1630,27)
        t("Date :",700,1630,23,True); t("Nom du producteur :",104,1540,20,True); t("Adresse :",104,1503,20,True); t("Point de collecte :",104,1466,20,True); t("Nom de l'agréeur :",700,1540,20,True); t("Quantité :",700,1503,20,True); t("N° Bon d'entrée :",700,1466,20,True)
        # text fields in PDF use saved layout
        c.setFont("Times-Roman",10)
        for k,(x,y,f,w,h) in self.layout_map.items():
            val=self.fields[k].text() if k in self.fields else (self.data.get(k,"") if k in HEADER_FIELDS else self.data.get("values",{}).get(k,""))
            if val: c.setFont("Times-Roman",f); c.drawString(x,H-y-f,val[:60])
        self._pdf_table(c,t)
        t("Référence : Décret n°88-152 du 26 juillet 1988 fixant les barèmes de bonification et de réfaction",104,240,14)
        t("applicables aux céréales et aux légumes secs.",104,218,14); t("Producteur",105,160,20,True); t("N° de la carte d’identité",105,100,19,True); t("Agréeur",1030,160,20,True,True)
        if self.data.get("status")=="REFUSED": self._pdf_notice(c,"PRODUIT REFUSÉ À CAUSE DE :",self.data.get("reason",""),690,H-653)
        elif self.result and self.result.price_to_discuss:self._pdf_notice(c,"PRIX À DÉBATTRE À CAUSE DE :",self.result.observation,690,H-653)
    def _pdf_table(self,c,t):
        x0,x1,x2,x3,x4,x5,x6=COLS; top=530; rows=rows_for(self.species); rh=62 if len(rows)<10 else 55; bottom=top+82+len(rows)*rh+50
        c.rect(x0,H-bottom,x6-x0,bottom-top); 
        for x in COLS[1:-1]: c.line(x,H-top,x,H-bottom)
        c.line(x0,H-612,x6,H-612)
        for i,(key,label,lim) in enumerate(rows):
            y=612+i*rh; c.line(x0,H-y-rh,x6,H-y-rh)
            c.setFont("Times-Bold",15); c.drawString(120,H-(y+rh/2),label); c.drawCentredString((x1+x2)/2,H-(y+rh/2),lim)
            if self.result:
                b,rf=self.result.rows.get(key,(0,0)); 
                if b:c.drawCentredString((x3+x4)/2,H-(y+rh/2),fmt(b))
                if rf:c.drawCentredString((x4+x5)/2,H-(y+rh/2),fmt(rf))
        c.setFont("Times-Bold",16); c.drawCentredString((x0+x2)/2,H-(bottom-25),"Total des Bonifications et Réfactions")
        if self.result:c.drawCentredString((x3+x4)/2,H-(bottom-25),fmt(self.result.bonus)); c.drawCentredString((x4+x5)/2,H-(bottom-25),fmt(self.result.refaction))
    def _pdf_notice(self,c,title,reason,x,y):
        c.setLineWidth(1.2); c.rect(x,y-105,480,105); c.setFont("Times-Bold",17); c.drawString(x+12,y-25,title); c.setFont("Times-Roman",13); c.drawString(x+12,y-50,(reason or "........................................")[:70])
