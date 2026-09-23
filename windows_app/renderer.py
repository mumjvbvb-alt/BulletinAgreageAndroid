from io import BytesIO
from pathlib import Path
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QPen, QFont, QImage, QFontDatabase
from PySide6.QtWidgets import QWidget, QLineEdit
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from logo_data import logo_image
from invoice_engine import RULES, fmt

W,H=1338,1900
COLS=(102,530,653,760,927,1063,1235)
_REPORTLAB_FONTS=Path(__import__("reportlab").__file__).resolve().parent/"fonts"
UI_FONT="Sans Serif"
_QT_FONT_READY=False
try:
    pdfmetrics.registerFont(TTFont("Vera",str(_REPORTLAB_FONTS/"Vera.ttf")))
    pdfmetrics.registerFont(TTFont("Vera-Bold",str(_REPORTLAB_FONTS/"VeraBd.ttf")))
    PDF_FONT="Vera"; PDF_BOLD="Vera-Bold"
except Exception:
    PDF_FONT="Helvetica"; PDF_BOLD="Helvetica-Bold"

def ensure_qt_font():
    global UI_FONT, _QT_FONT_READY
    if _QT_FONT_READY:return
    try:
        reg=QFontDatabase.addApplicationFont(str(_REPORTLAB_FONTS/"Vera.ttf"))
        fam=QFontDatabase.applicationFontFamilies(reg) if reg >= 0 else []
        if fam:UI_FONT=fam[0]
    except Exception:
        UI_FONT="Sans Serif"
    _QT_FONT_READY=True

HEADER_FIELDS={
 "date":(805,246,225,32),"producer":(380,336,155,32),"address":(250,373,285,32),
 "point":(340,410,285,32),"agreer":(940,336,155,32),"quantity":(835,373,175,32),
 "bon":(885,410,165,32),"producer_id":(110,1778,360,38)
}

def rows_for(species):
    if species=="Blé Dur":
        return [
        ("poids","Poids spécifique (kg/hl)","[76 – 80]"),
        ("humidite","Teneur en eau (%)","≤ 17"),
        ("ergot","Ergot (‰)","≤ 1"),
        ("tamis","Matières qui passent à travers\nle tamis 20 mm x 2,1 mm (%)","—"),
        ("debris","Débris végétaux et éléments minéraux\nretenus par le tamis 20 mm x 2,1 mm (%)","—"),
        ("graines_nuisibles","Graines nuisibles (%)","≤ 0,25"),
        ("impur1","Total (%)","[1 – 3]"),
        ("casses","Grains cassés (%)","≤ 5"),
        ("boutes","Grains fortement boutés (%)","≤ 5"),
        ("roux","Grains roux (%)","—"),
        ("mouchetes","Grains fortement mouchetés (%)","—"),
        ("punaises","Grains punaisés (%)","—"),
        ("piques","Grains piqués (%)","—"),
        ("impur2","Total (%)","≤ 10"),
        ("mitadin","Grains mitadinés (%)","—"),
        ("ble_tendre","Blé tendre dans blé dur (%)","≤ 5"),
        ("mitadin_total","Total (%)","[10 – 20]")]
    if species=="Blé Tendre":
        return [
        ("poids","Poids spécifique (kg/hl)","[74 – 77]"),
        ("humidite","Teneur en eau (%)","≤ 17"),
        ("ergot","Ergot (‰)","< 0,01"),
        ("tamis","Matières qui passent à travers\nle tamis 20 mm x 2,1 mm (%)","—"),
        ("debris","Débris végétaux et éléments minéraux\nretenus par le tamis 20 mm x 2,1 mm (%)","—"),
        ("graines_nuisibles","Graines nuisibles (%)","≤ 0,25"),
        ("impur1","Total (%)","[1 – 3]"),
        ("casses","Grains cassés (%)","≤ 4"),
        ("punaises","Grains punaisés (%)","≤ 2"),
        ("boutes_forts","Grains fortement boutés (%)","—"),
        ("boutes_faibles","Grains faiblement boutés (%)","—"),
        ("mouchetes","Grains fortement mouchetés (%)","—"),
        ("graines_betail","Graines étrangères utilisables\npour le bétail (%)","—"),
        ("impur2","Total (%)","≤ 6")]
    return [
        ("poids","Poids spécifique (kg/hl)","[58 – 62]"),
        ("humidite","Teneur en eau (%)","≤ 17"),
        ("grains_sans_valeur","Grains sans valeur (%)","—"),
        ("impurites","Matières inertes (%)","—"),
        ("impurites_total","Total (%)","≤ 2"),
        ("ergot","Ergot (‰)","≤ 1")]

class InvoicePreview(QWidget):
    def __init__(self,parent=None):
        ensure_qt_font()
        super().__init__(parent)
        self.species="Blé Dur"; self.data={}; self.result=None
        self.layout_map={}; self.edit_mode=False; self.edits={}; self.fields={}
        self.zoom=1.0; self.setMinimumSize(620,720); self.setStyleSheet("background:#e9e9e9;")
    def set_zoom(self,value):
        self.zoom=max(.75,min(1.5,float(value))); self.relayout(); self.update()
    def _notice_needed(self):
        return self.data.get("status")=="REFUSED" or bool(self.result and self.result.price_to_discuss)

    def _field_value(self,key):
        if key in HEADER_FIELDS:return str(self.data.get(key,""))
        if key=="notice_title":
            v=self.data.get("values",{}).get("notice_title","")
            return v or ("PRODUIT REFUSÉ À CAUSE DE :" if self.data.get("status")=="REFUSED" else "PRIX À DÉBATTRE À CAUSE DE :")
        if key=="notice_reason":
            return str(self.data.get("values",{}).get("notice_reason","") or self.data.get("reason","") or (self.result.observation if self.result else ""))
        return str(self.data.get("values",{}).get(key,""))

    def set_data(self,data,result):
        old_species=self.species
        old_notice=self._notice_needed()
        self.data=data; self.result=result; self.species=data.get("species","Blé Dur")
        new_notice=self._notice_needed()
        if not self.fields or old_species!=self.species or old_notice!=new_notice:
            self.rebuild_fields()
        else:
            self.refresh_field_texts()
            self.relayout()
        self.update()
    def rebuild_fields(self):
        for w in list(self.fields.values()):
            w.hide(); w.setParent(None); w.deleteLater()
        self.fields={}
        defaults=dict(HEADER_FIELDS)
        y=638
        for key,_,_ in rows_for(self.species):
            defaults[key]=(655,y+4,105,30); y+=40
        notice_needed=self.data.get("status")=="REFUSED" or bool(self.result and self.result.price_to_discuss)
        if notice_needed:
            defaults["notice_title"]=(690,548,480,34)
            defaults["notice_reason"]=(702,590,456,48)
        for key,(x,y,w,h) in defaults.items():
            conf=self.edits.get(key,{})
            self.layout_map[key]=(float(conf.get("x",x)),float(conf.get("y",y)),float(conf.get("font",10)),w,h)
            e=QLineEdit(self)
            val=self._field_value(key)
            e.setText(str(val))
            e.setFrame(False); e.setAlignment(Qt.AlignCenter if key not in HEADER_FIELDS and key not in ("notice_title","notice_reason") else Qt.AlignLeft|Qt.AlignVCenter)
            e.setStyleSheet("background:transparent;color:#000;border:none;padding:0;")
            e.setFont(QFont(UI_FONT,max(6,int(self.layout_map[key][2]))))
            e.setReadOnly(True)
            e.setEnabled(True)
            e.textChanged.connect(lambda _,k=key:self._changed(k))
            self.fields[key]=e
        self.relayout()

    def refresh_field_texts(self):
        for key,e in self.fields.items():
            val=self._field_value(key)
            if e.text()!=val:
                e.blockSignals(True); e.setText(val); e.blockSignals(False)

    def _changed(self,key):
        if key in HEADER_FIELDS:self.data[key]=self.fields[key].text()
        elif key=="notice_title":self.data.setdefault("values",{})["notice_title"]=self.fields[key].text()
        elif key=="notice_reason":self.data.setdefault("values",{})["notice_reason"]=self.fields[key].text()
        else:self.data.setdefault("values",{})[key]=self.fields[key].text()
        self.update()
    def relayout(self):
        s=min(self.width()/W,self.height()/H)*self.zoom
        ox=(self.width()-W*s)/2; oy=(self.height()-H*s)/2
        for k,e in self.fields.items():
            x,y,f,w,h=self.layout_map[k]
            e.setGeometry(int(ox+x*s),int(oy+y*s),max(2,int(w*s)),max(2,int(h*s)))
            e.setFont(QFont(UI_FONT,max(6,int(f*s))))
            e.setVisible(True)
    def resizeEvent(self,e):
        self.relayout(); super().resizeEvent(e)
    def set_edit_mode(self,on):
        self.edit_mode=on
        for e in self.fields.values():
            e.setReadOnly(not on)
            e.setEnabled(True)
        self.update()
    def set_layout(self,key,x,y,font):
        if key not in self.layout_map:return
        _,_,_,w,h=self.layout_map[key]; self.layout_map[key]=(x,y,font,w,h)
        self.edits[key]={"x":x,"y":y,"font":font}; self.relayout(); self.update()
    def reset_layout(self):
        self.edits={}; self.rebuild_fields()
    def layout_json(self): return self.edits
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        s=min(self.width()/W,self.height()/H)*self.zoom
        ox=(self.width()-W*s)/2; oy=(self.height()-H*s)/2
        p.translate(ox,oy); p.scale(s,s); self.draw_page(p); p.end()
    def draw_page(self,p):
        p.fillRect(0,0,W,H,Qt.white)
        p.setPen(QPen(Qt.black,1.4))
        p.drawRect(14,14,W-28,H-28)
        try:
            im=logo_image(); raw=BytesIO(); im.save(raw,format="PNG"); q=QImage.fromData(raw.getvalue())
            p.drawImage(QRectF(30,30,82,82),q); p.drawImage(QRectF(W-112,30,82,82),q)
        except Exception: pass
        def txt(t,x,y,size,bold=False,align=Qt.AlignLeft,w=300):
            f=QFont(UI_FONT,size); f.setBold(bold); p.setFont(f)
            p.drawText(QRectF(x,y-size,w,size+8),Qt.TextWordWrap|align,t)
        txt("OFFICE ALGERIEN INTERPROFESSIONNEL DES CEREALES",130,78,23,True,Qt.AlignCenter,1078)
        txt("Coopérative de Céréales et des Légumes Secs de BATNA",170,125,18,True,Qt.AlignCenter,998)
        txt("Bulletin d'Agréage",330,192,27,True,Qt.AlignCenter,678)
        txt("Espèce :",104,260,16,True); txt(self.species,235,260,18)
        txt("Date :",700,260,16,True); txt("Nom du producteur :",104,346,15,True); txt("Adresse :",104,383,15,True)
        txt("Point de collecte :",104,420,15,True); txt("Nom de l'agréeur :",700,346,15,True)
        txt("Quantité :",700,383,15,True); txt("Bulletin d'Agréage N° :",700,420,15,True)
        self.draw_table(p,txt)
        txt("Référence : Décret n°88-152 du 26 juillet 1988 fixant les barèmes de bonification et de réfaction",104,1660,11)
        txt("applicables aux céréales et aux légumes secs. Ière partie : Relations entre producteurs et organismes stockeurs.",104,1680,11)
        txt("Producteur",105,1738,15,True); txt("N° de la carte d’identité",105,1800,14,True); txt("Agréeur",1030,1738,15,True,Qt.AlignCenter,180)
        status=self.data.get("status","ACCEPTED")
        if status=="REFUSED" or (self.result and self.result.price_to_discuss): self.draw_notice_box(p)
    def draw_table(self,p,txt):
        x0,x1,x2,x3,x4,x5,x6=COLS; top=515; rows=rows_for(self.species); rh=55 if len(rows)>=15 else (68 if len(rows)>=8 else 86)
        bottom=top+82+len(rows)*rh+48
        p.drawRect(x0,top,x6-x0,bottom-top)
        for x in COLS[1:-1]:p.drawLine(x,top,x,bottom)
        p.drawLine(x0,597,x6,597)
        txt("Paramètres",x0,572,15,True,Qt.AlignCenter,x1-x0)
        txt("Limites\n(sans bonification ni réfaction)",x1,552,12,True,Qt.AlignCenter,x2-x1)
        txt("Valeurs",x2,572,14,True,Qt.AlignCenter,x3-x2)
        txt("Bonification\n(D.A.)",x3,552,12,True,Qt.AlignCenter,x4-x3)
        txt("Réfaction\n(D.A.)",x4,552,12,True,Qt.AlignCenter,x5-x4)
        txt("Observation",x5,572,12,True,Qt.AlignCenter,x6-x5)
        for i,(key,label,lim) in enumerate(rows):
            y=597+i*rh; p.drawLine(x0,y+rh,x6,y+rh)
            txt(label,x0+10,y+rh/2+6,10,True,Qt.AlignLeft,x1-x0-18)
            txt(lim,(x1+x2)/2,y+rh/2+6,10,False,Qt.AlignCenter,x2-x1)
            if self.result:
                b,rf=self.result.rows.get(key,(0,0))
                if b: txt(fmt(b),x3,y+rh/2+6,10,True,Qt.AlignCenter,x4-x3)
                if rf: txt(fmt(rf),x4,y+rh/2+6,10,True,Qt.AlignCenter,x5-x4)
                obs=self.result.observations.get(key,"")
                if obs: txt(obs,x5,y+rh/2+6,8,False,Qt.AlignCenter,x6-x5-6)
        y=bottom-24; txt("Total des Bonifications et Réfactions",x0,y,10,True,Qt.AlignCenter,x2-x0)
        if self.result:
            txt(fmt(self.result.bonus),x3,y,10,True,Qt.AlignCenter,x4-x3)
            txt(fmt(self.result.refaction),x4,y,10,True,Qt.AlignCenter,x5-x4)
    def draw_notice_box(self,p):
        conf=self.layout_map.get("notice_title",(690,548,14,480,34))
        x,y,f,w,h=conf
        p.setPen(QPen(Qt.black,1.8)); p.drawRect(x,y,w,105)
        # editing overlays carry the actual editable text
    def pdf(self,path):
        c=canvas.Canvas(str(path),pagesize=A4)
        sx=A4[0]/W; sy=A4[1]/H
        c.saveState(); c.scale(sx,sy); c.setLineWidth(.8); c.setFillColorRGB(0,0,0); self._pdf_page(c); c.restoreState(); c.save()
    def _pdf_page(self,c):
        c.setFillColorRGB(1,1,1); c.rect(0,0,W,H,fill=1,stroke=0); c.setFillColorRGB(0,0,0); c.setLineWidth(.8); c.rect(14,14,W-28,H-28)
        try:
            im=logo_image(); bio=BytesIO(); im.save(bio,format="PNG"); bio.seek(0)
            c.drawImage(ImageReader(bio),30,H-112,82,82,mask="auto"); c.drawImage(ImageReader(bio),W-112,H-112,82,82,mask="auto")
        except Exception: pass
        def t(s,x,y,size=12,b=False,center=False,w=300):
            c.setFont(PDF_BOLD if b else PDF_FONT,size)
            if center:c.drawCentredString(x,y,s)
            else:c.drawString(x,y,s)
        t("OFFICE ALGERIEN INTERPROFESSIONNEL DES CEREALES",669,1822,23,True,True)
        t("Coopérative de Céréales et des Légumes Secs de BATNA",669,1775,18,True,True)
        t("Bulletin d'Agréage",669,1708,27,True,True)
        t("Espèce :",104,1640,16,True); t(self.species,235,1640,18)
        t("Date :",700,1640,16,True); t("Nom du producteur :",104,1554,15,True); t("Adresse :",104,1517,15,True)
        t("Point de collecte :",104,1480,15,True); t("Nom de l'agréeur :",700,1554,15,True); t("Quantité :",700,1517,15,True); t("Bulletin d'Agréage N° :",700,1480,15,True)
        for k,(x,y,f,w,h) in self.layout_map.items():
            if k not in self.fields: continue
            val=self.fields[k].text()
            if not val: continue
            c.setFont(PDF_FONT,max(6,f))
            c.drawString(x,H-y-f,val[:100])
        self._pdf_table(c,t)
        t("Référence : Décret n°88-152 du 26 juillet 1988 fixant les barèmes de bonification et de réfaction",104,240,11)
        t("applicables aux céréales et aux légumes secs. Ière partie : Relations entre producteurs et organismes stockeurs.",104,222,11)
        t("Producteur",105,160,15,True); t("N° de la carte d’identité",105,100,14,True); t("Agréeur",1030,160,15,True,True)
        if self.data.get("status")=="REFUSED" or (self.result and self.result.price_to_discuss): self._pdf_notice(c)
    def _pdf_table(self,c,t):
        x0,x1,x2,x3,x4,x5,x6=COLS; top=515; rows=rows_for(self.species); rh=61 if len(rows)>=15 else (68 if len(rows)>=8 else 86); bottom=top+82+len(rows)*rh+48
        c.rect(x0,H-bottom,x6-x0,bottom-top)
        for x in COLS[1:-1]:c.line(x,H-top,x,H-bottom)
        c.line(x0,H-597,x6,H-597)
        for i,(key,label,lim) in enumerate(rows):
            y=597+i*rh; c.line(x0,H-y-rh,x6,H-y-rh)
            c.setFont(PDF_BOLD,10); c.drawString(x0+10,H-(y+rh/2),label.replace("\\n"," "))
            c.setFont(PDF_FONT,10); c.drawCentredString((x1+x2)/2,H-(y+rh/2),lim)
            if self.result:
                b,rf=self.result.rows.get(key,(0,0))
                if b:c.drawCentredString((x3+x4)/2,H-(y+rh/2),fmt(b))
                if rf:c.drawCentredString((x4+x5)/2,H-(y+rh/2),fmt(rf))
        c.setFont(PDF_BOLD,10); c.drawCentredString((x0+x2)/2,H-(bottom-24),"Total des Bonifications et Réfactions")
        if self.result:
            c.drawCentredString((x3+x4)/2,H-(bottom-24),fmt(self.result.bonus)); c.drawCentredString((x4+x5)/2,H-(bottom-24),fmt(self.result.refaction))
    def _pdf_notice(self,c):
        if "notice_title" not in self.layout_map:return
        x,y,f,w,h=self.layout_map["notice_title"]
        c.setLineWidth(1.1); c.rect(x,H-y-105,w,105)
        title=self.fields.get("notice_title").text() if self.fields.get("notice_title") else ""
        reason=self.fields.get("notice_reason").text() if self.fields.get("notice_reason") else ""
        c.setFont(PDF_BOLD,max(8,f)); c.drawString(x+12,H-y-24,title[:90])
        c.setFont(PDF_FONT,max(7,f-2)); c.drawString(x+12,H-y-50,reason[:90])
