import sys, os, json, shutil
from pathlib import Path
from datetime import date, datetime
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import *
from database import Database
from invoice_engine import SPECIES,RULES,calculate,num,fmt
from renderer import InvoicePreview

ROOT=Path.home()/"Documents"/"Bulletin d’Agréage"
PDF_ROOT=ROOT/"PDF"
BACKUP_ROOT=ROOT/"Backups"

class LayoutDialog(QDialog):
    def __init__(self,preview,parent=None):
        super().__init__(parent); self.preview=preview; self.setWindowTitle("Modifier la mise en page"); self.resize(520,430)
        lay=QFormLayout(self); self.field=QComboBox(); self.field.addItems(preview.fields.keys())
        self.x=QDoubleSpinBox(); self.x.setRange(0,1338); self.y=QDoubleSpinBox(); self.y.setRange(0,1900); self.font=QDoubleSpinBox(); self.font.setRange(6,30); self.font.setSingleStep(.5)
        for w in (self.x,self.y,self.font):w.setDecimals(1)
        lay.addRow("Champ",self.field); lay.addRow("Position X",self.x); lay.addRow("Position Y",self.y); lay.addRow("Taille du texte",self.font)
        buttons=QHBoxLayout(); up=QPushButton("↑"); dn=QPushButton("↓"); lf=QPushButton("←"); rt=QPushButton("→")
        for b in (up,dn,lf,rt):buttons.addWidget(b)
        lay.addRow("Déplacement",buttons)
        reset=QPushButton("Réinitialiser la mise en page"); reset.clicked.connect(preview.reset_layout)
        buttons2=QHBoxLayout(); done=QPushButton("Terminer"); cancel=QPushButton("Annuler"); buttons2.addWidget(reset); buttons2.addStretch(); buttons2.addWidget(cancel); buttons2.addWidget(done); lay.addRow(buttons2)
        self.field.currentTextChanged.connect(self.load); self.x.valueChanged.connect(self.apply); self.y.valueChanged.connect(self.apply); self.font.valueChanged.connect(self.apply)
        up.clicked.connect(lambda:self.move(0,-1)); dn.clicked.connect(lambda:self.move(0,1)); lf.clicked.connect(lambda:self.move(-1,0)); rt.clicked.connect(lambda:self.move(1,0))
        done.clicked.connect(self.accept); cancel.clicked.connect(self.reject); self.load(self.field.currentText())
    def load(self,key):
        x,y,f,_,_=self.preview.layout_map[key]; self.x.blockSignals(True); self.y.blockSignals(True); self.font.blockSignals(True)
        self.x.setValue(x); self.y.setValue(y); self.font.setValue(f)
        self.x.blockSignals(False); self.y.blockSignals(False); self.font.blockSignals(False)
    def apply(self):
        self.preview.set_layout(self.field.currentText(),self.x.value(),self.y.value(),self.font.value())
    def move(self,dx,dy):
        self.x.setValue(self.x.value()+dx); self.y.setValue(self.y.value()+dy)

class HistoryDialog(QDialog):
    def __init__(self,db,parent):
        super().__init__(parent); self.db=db; self.selected=None; self.setWindowTitle("Historique des factures"); self.resize(800,500)
        lay=QVBoxLayout(self); row=QHBoxLayout(); self.search=QLineEdit(); self.search.setPlaceholderText("Producteur, N° Bon ou Date"); row.addWidget(self.search); b=QPushButton("Rechercher"); row.addWidget(b); lay.addLayout(row)
        self.table=QTableWidget(0,6); self.table.setHorizontalHeaderLabels(["N° Bon","Date","Espèce","Producteur","Statut","ID"]); self.table.setSelectionBehavior(QAbstractItemView.SelectRows); self.table.setEditTriggers(QAbstractItemView.NoEditTriggers); lay.addWidget(self.table)
        row2=QHBoxLayout(); load=QPushButton("Ouvrir"); clone=QPushButton("Dupliquer"); delete=QPushButton("Supprimer"); close=QPushButton("Fermer")
        for x in (load,clone,delete):row2.addWidget(x)
        row2.addStretch(); row2.addWidget(close); lay.addLayout(row2)
        self.search.textChanged.connect(self.refresh); b.clicked.connect(self.refresh); load.clicked.connect(self.open); clone.clicked.connect(self.duplicate); delete.clicked.connect(self.remove); close.clicked.connect(self.reject); self.table.doubleClicked.connect(lambda _:self.open()); self.refresh()
    def refresh(self):
        rows=self.db.history(self.search.text()); self.table.setRowCount(len(rows))
        for i,r in enumerate(rows):
            vals=[r["bon_number"],r["invoice_date"],r["species"],r["producer"],r["status"],r["id"]]
            for j,v in enumerate(vals):self.table.setItem(i,j,QTableWidgetItem(str(v or "")))
        self.table.hideColumn(5)
    def id(self):
        r=self.table.currentRow(); return int(self.table.item(r,5).text()) if r>=0 else None
    def open(self):
        self.selected=("open",self.id()) if self.id() else None
        if self.selected:self.accept()
    def duplicate(self):
        self.selected=("duplicate",self.id()) if self.id() else None
        if self.selected:self.accept()
    def remove(self):
        i=self.id()
        if i and QMessageBox.question(self,"Confirmation","Voulez-vous vraiment supprimer cette facture ?",QMessageBox.Yes|QMessageBox.No)==QMessageBox.Yes:self.db.delete_invoice(i); self.refresh()

class SettingsDialog(QDialog):
    def __init__(self,db,parent=None):
        super().__init__(parent); self.db=db; self.setWindowTitle("Paramètres"); self.resize(620,430)
        lay=QFormLayout(self)
        self.lang=QComboBox(); self.lang.addItems(["Français","العربية","English"]); self.lang.setCurrentText(db.setting("language","Français"))
        self.ag=QLineEdit(db.setting("agreer","")); self.point=QLineEdit(db.setting("collection_point",""))
        self.pdf=QLineEdit(db.setting("pdf_folder",str(PDF_ROOT))); self.back=QLineEdit(db.setting("backup_folder",str(BACKUP_ROOT)))
        self.daily=QCheckBox("Sauvegarde automatique quotidienne"); self.daily.setChecked(db.setting("daily_backup","1")=="1")
        self.closeb=QCheckBox("Sauvegarde à la fermeture"); self.closeb.setChecked(db.setting("close_backup","1")=="1")
        lay.addRow("Langue de l’interface",self.lang); lay.addRow("Nom de l’agréeur",self.ag); lay.addRow("Point de collecte par défaut",self.point)
        for label,w in [("Dossier PDF",self.pdf),("Dossier sauvegardes",self.back)]: lay.addRow(label,w)
        lay.addRow("",self.daily); lay.addRow("",self.closeb)
        buttons=QHBoxLayout(); ok=QPushButton("Enregistrer"); cancel=QPushButton("Annuler"); buttons.addStretch(); buttons.addWidget(cancel); buttons.addWidget(ok); lay.addRow(buttons)
        ok.clicked.connect(self.save); cancel.clicked.connect(self.reject)
    def choose(self,w):
        p=QFileDialog.getExistingDirectory(self,"Choisir un dossier",w.text())
        if p:w.setText(p)
    def save(self):
        for k,w in [("language",self.lang),("agreer",self.ag),("collection_point",self.point),("pdf_folder",self.pdf),("backup_folder",self.back)]:self.db.save_setting(k,w.currentText() if isinstance(w,QComboBox) else w.text())
        self.db.save_setting("daily_backup","1" if self.daily.isChecked() else "0"); self.db.save_setting("close_backup","1" if self.closeb.isChecked() else "0"); self.accept()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); ROOT.mkdir(parents=True,exist_ok=True); PDF_ROOT.mkdir(parents=True,exist_ok=True); BACKUP_ROOT.mkdir(parents=True,exist_ok=True)
        self.db=Database(ROOT/"bulletin.db"); self.invoice_id=None; self.last_saved=None; self.setWindowTitle("Bulletin d’Agréage — Professionnel"); self.resize(1600,950)
        self.build(); self.new_invoice(); self.daily_backup()
        self.timer=QTimer(self); self.timer.timeout.connect(self.autosave); self.timer.start(30000)
    def build(self):
        mb=self.menuBar(); fm=mb.addMenu("Fichier")
        for label,fn in [("Nouvelle facture",self.new_invoice),("Historique",self.history),("Exporter PDF",self.export_pdf),("Imprimer",self.print_invoice),("Quitter",self.close)]:a=QAction(label,self);a.triggered.connect(fn);fm.addAction(a)
        tools=mb.addMenu("Outils"); a=QAction("Modifier la mise en page",self);a.triggered.connect(self.edit_layout);tools.addAction(a); a=QAction("Réinitialiser la mise en page",self);a.triggered.connect(self.reset_layout);tools.addAction(a)
        settings=QAction("Paramètres",self);settings.triggered.connect(self.settings);mb.addAction(settings)
        splitter=QSplitter(Qt.Horizontal); splitter.addWidget(self.input_panel()); self.preview=InvoicePreview(); splitter.addWidget(self.preview); splitter.setSizes([500,1050]); self.setCentralWidget(splitter)
    def input_panel(self):
        root=QWidget(); out=QVBoxLayout(root); scroll=QScrollArea(); scroll.setWidgetResizable(True); body=QWidget(); lay=QVBoxLayout(body)
        box=QGroupBox("Données de la facture"); f=QFormLayout(box)
        self.species=QComboBox(); self.species.addItems(SPECIES); f.addRow("Espèce",self.species)
        self.date=QDateEdit(); self.date.setCalendarPopup(True); self.date.setDate(__import__("PySide6").QtCore.QDate.currentDate()); f.addRow("Date",self.date)
        self.producer=QComboBox(); self.producer.setEditable(True); f.addRow("Nom du producteur",self.producer)
        self.address=QLineEdit(); f.addRow("Adresse",self.address); self.idcard=QLineEdit(); f.addRow("N° carte d’identité",self.idcard)
        self.agreer=QLineEdit(); f.addRow("Nom de l’agréeur",self.agreer); self.quantity=QLineEdit(); f.addRow("Quantité (Qx)",self.quantity)
        self.point=QLineEdit(); f.addRow("Point de collecte",self.point); self.bon=QLineEdit(); f.addRow("N° Bon d’entrée",self.bon)
        self.status=QComboBox(); self.status.addItems(["ACCEPTED","REFUSED"]); f.addRow("Décision",self.status)
        self.reason=QComboBox(); self.reason.setEditable(True); f.addRow("Cause du refus",self.reason)
        lay.addWidget(box); self.analysis=QGroupBox("Analyses — entrer les Valeurs uniquement"); self.af=QFormLayout(self.analysis); lay.addWidget(self.analysis)
        self.notice=QLabel(); self.notice.setWordWrap(True); lay.addWidget(self.notice)
        row=QHBoxLayout(); reset=QPushButton("Réinitialiser"); save=QPushButton("Enregistrer"); pdf=QPushButton("Exporter PDF"); hist=QPushButton("Historique")
        for b,fn in [(reset,self.reset_analysis),(save,self.save_invoice),(pdf,self.export_pdf),(hist,self.history)]:b.clicked.connect(fn);row.addWidget(b)
        lay.addLayout(row); lay.addStretch(); scroll.setWidget(body); out.addWidget(scroll)
        self.species.currentTextChanged.connect(self.rebuild_analysis); self.producer.currentTextChanged.connect(self.producer_changed); self.status.currentTextChanged.connect(self.changed); self.reason.currentTextChanged.connect(self.changed)
        return root
    def rebuild_analysis(self,*_):
        while self.af.rowCount():self.af.removeRow(0)
        self.analysis_fields={}
        for r in RULES[self.species.currentText()]:
            e=QLineEdit(); e.setPlaceholderText(f"{r.unit}"); e.setAlignment(Qt.AlignCenter); e.textChanged.connect(self.changed)
            ref=QLabel(r.reference); ref.setStyleSheet("color:#555"); self.analysis_fields[r.key]=e; self.af.addRow(r.label,e); self.af.addRow("Valeur de référence",ref)
        self.update_preview()
    def producer_changed(self,*_):
        name=self.producer.currentText()
        for r in self.db.producers():
            if r["name"]==name:self.address.setText(r["address"] or "");self.idcard.setText(r["identity_number"] or "");break
        self.changed()
    def changed(self,*_):
        self.update_preview()
    def collect(self):
        vals={k:e.text() for k,e in self.analysis_fields.items()}; return {"species":self.species.currentText(),"date":self.date.date().toString("dd/MM/yyyy"),"producer":self.producer.currentText(),"address":self.address.text(),"producer_id":self.idcard.text(),"agreer":self.agreer.text(),"quantity_qx":num(self.quantity.text()),"point":self.point.text(),"bon_number":int(self.bon.text() or self.db.next_bon()),"status":self.status.currentText(),"reason":self.reason.currentText(),"values":vals,"layout":self.preview.layout_json()}
    def update_preview(self):
        if not hasattr(self,"analysis_fields"):return
        d=self.collect() if self.bon.text() else {"species":self.species.currentText(),"values":{}}
        res=calculate(d["species"],d.get("values",{})); self.preview.set_data(d,res)
        self.notice.setText(("PRIX À DÉBATTRE" if res.price_to_discuss else "")+((" — "+res.observation) if res.observation else ""))
    def new_invoice(self):
        self.invoice_id=None; self.species.setCurrentText("Blé Dur"); self.rebuild_analysis(); self.date.setDate(__import__("PySide6").QtCore.QDate.currentDate())
        self.bon.setText(str(self.db.next_bon())); self.producer.setCurrentText(""); self.address.clear(); self.idcard.clear(); self.agreer.setText(self.db.setting("agreer","")); self.quantity.clear(); self.point.setText(self.db.setting("collection_point","")); self.status.setCurrentText("ACCEPTED"); self.reason.clear(); self.preview.reset_layout(); self.preview.set_data(self.collect(),calculate(self.species.currentText(),{}))
    def reset_analysis(self):
        if QMessageBox.question(self,"Confirmation","Voulez-vous vraiment réinitialiser les valeurs d’analyse ?",QMessageBox.Yes|QMessageBox.No)!=QMessageBox.Yes:return
        for e in self.analysis_fields.values():e.clear()
    def save_invoice(self):
        d=self.collect()
        if not d["producer"].strip():QMessageBox.warning(self,"Validation","Veuillez saisir le nom du producteur.");return
        try:self.invoice_id=self.db.save_invoice(d,self.invoice_id); self.db.save_producer(d["producer"],d["address"],d["producer_id"]); self.last_saved=d.copy(); QMessageBox.information(self,"Enregistrer","Facture enregistrée avec succès.")
        except sqlite3.IntegrityError: QMessageBox.warning(self,"N° Bon","Ce N° Bon existe déjà.")
    def load_invoice(self,i,duplicate=False):
        d=self.db.get_invoice(i)
        if not d:return
        self.invoice_id=None if duplicate else d["id"]; self.species.setCurrentText(d["species"]); self.date.setDate(__import__("PySide6").QtCore.QDate.fromString(d["invoice_date"],"dd/MM/yyyy")); self.producer.setCurrentText(d["producer"] or ""); self.address.setText(d["address"] or ""); self.idcard.setText(d["producer_id"] or ""); self.agreer.setText(d["agreer"] or ""); self.quantity.setText(fmt(d["quantity_qx"])); self.point.setText(d["collection_point"] or ""); self.bon.setText(str(self.db.next_bon() if duplicate else d["bon_number"])); self.status.setCurrentText(d["status"]); self.reason.setCurrentText(d["reason"] or "")
        for k,e in self.analysis_fields.items():e.setText(str(d["values"].get(k,"")))
        self.preview.edits=d.get("layout",{}); self.update_preview()
    def history(self):
        h=HistoryDialog(self.db,self)
        if h.exec()==QDialog.Accepted and h.selected:self.load_invoice(h.selected[1],h.selected[0]=="duplicate")
    def edit_layout(self):
        self.preview.edit_mode=True; d=LayoutDialog(self.preview,self); d.exec(); self.preview.edit_mode=False; self.update_preview()
    def reset_layout(self):
        if QMessageBox.question(self,"Confirmation","Réinitialiser la mise en page de tous les champs ?",QMessageBox.Yes|QMessageBox.No)==QMessageBox.Yes:self.preview.reset_layout();self.update_preview()
    def export_pdf(self):
        d=self.collect(); dt=datetime.strptime(d["date"],"%d/%m/%Y"); folder=Path(self.db.setting("pdf_folder",str(PDF_ROOT)))/f"{dt.year:04d}"/f"{dt.month:02d}"/f"{dt.day:02d}"; folder.mkdir(parents=True,exist_ok=True)
        safe="".join(c if c.isalnum() or c in " _-" else "_" for c in d["producer"]).strip().replace(" ","_") or "Producteur"; base=f"Bon_{d['bon_number']}_{safe}_{dt.strftime('%d-%m-%Y')}"; path=folder/(base+".pdf"); n=2
        while path.exists():path=folder/(base+f"_{n}.pdf");n+=1
        self.preview.pdf(path); QMessageBox.information(self,"PDF",f"PDF créé avec succès.\n{path}")
    def print_invoice(self):
        import tempfile
        path=Path(tempfile.gettempdir())/f"Bulletin_{self.bon.text()}.pdf"; self.preview.pdf(path)
        try:os.startfile(str(path),"print")
        except Exception:os.startfile(str(path))
    def settings(self):
        if SettingsDialog(self.db,self).exec()==QDialog.Accepted:
            self.agreer.setText(self.db.setting("agreer","")); self.point.setText(self.db.setting("collection_point","")); self.load_reasons()
    def load_reasons(self):
        self.reason.clear(); self.reason.addItems(self.db.reasons("REFUSED"))
    def daily_backup(self):
        if self.db.setting("daily_backup","1")!="1":return
        stamp=date.today().isoformat()
        if self.db.setting("last_backup_date","")!=stamp:
            p=Path(self.db.setting("backup_folder",str(BACKUP_ROOT)))/f"BulletinBackup_{stamp}.backup"; self.db.backup(p); self.db.save_setting("last_backup_date",stamp)
    def autosave(self):
        if not self.producer.currentText().strip():return
        try:self.db.save_invoice(self.collect(),self.invoice_id)
        except Exception:pass
    def closeEvent(self,e):
        try:
            if self.db.setting("close_backup","1")=="1":
                p=Path(self.db.setting("backup_folder",str(BACKUP_ROOT)))/f"BulletinBackup_{date.today().isoformat()}_fermeture.backup"; self.db.backup(p)
        finally:self.db.close();e.accept()

def main():
    from PySide6.QtWidgets import QApplication
    app=QApplication(sys.argv); app.setStyle("Fusion"); app.setFont(QFont("Segoe UI",10)); w=MainWindow(); w.show(); sys.exit(app.exec())

if __name__=="__main__":main()
