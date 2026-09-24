import sys, os, json, shutil, sqlite3
from pathlib import Path
from datetime import date, datetime
from PySide6.QtCore import Qt, QTimer, QDate
from PySide6.QtGui import QFont, QAction
from PySide6.QtWidgets import *
from database import Database
from invoice_engine import SPECIES,RULES,calculate,num,fmt
import renderer
from renderer import InvoicePreview

def today_text():
    d=QDate.currentDate()
    return f"{d.day():02d}/{d.month():02d}/{d.year():04d}"

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
        buttons=QHBoxLayout(); up=QPushButton("Haut"); dn=QPushButton("Bas"); lf=QPushButton("Gauche"); rt=QPushButton("Droite")
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
        self.db=Database(ROOT/"bulletin.db"); self.invoice_id=None; self.last_saved=None; self.setWindowTitle("Bulletin d’Agréage — Professionnel"); self.resize(1650,980)
        self.build(); self.load_producers(); self.load_reasons(); self.new_invoice(clear_draft=False); self.daily_backup(); self.recover_draft()
        self.timer=QTimer(self); self.timer.timeout.connect(self.autosave); self.timer.start(30000)
        self.draft_timer=QTimer(self); self.draft_timer.setSingleShot(True); self.draft_timer.timeout.connect(self.write_draft)
    def build(self):
        self.setStyleSheet("""
            QMainWindow { background:#eceff1; }
            QGroupBox { font-weight:600; border:1px solid #b8bec4; border-radius:6px; margin-top:8px; padding-top:10px; background:#ffffff; }
            QGroupBox::title { subcontrol-origin:margin; left:10px; padding:0 5px; }
            QLineEdit, QComboBox { min-height:30px; padding:2px 7px; border:1px solid #aeb5bb; border-radius:4px; background:#fff; }
            QLineEdit:focus, QComboBox:focus { border:2px solid #5b7c99; }
            QPushButton { min-height:32px; padding:3px 12px; border:1px solid #9aa3aa; border-radius:4px; background:#f8f9fa; }
            QPushButton:hover { background:#e8edf1; }
            QHeaderView::section { padding:5px; font-weight:600; }
        """)
        mb=self.menuBar(); fm=mb.addMenu("Fichier")
        for label,fn in [("Nouvelle facture",self.new_invoice),("Historique",self.history),("Annuler les modifications",self.revert_saved),("Exporter PDF",self.export_pdf),("Imprimer",self.print_invoice),("Quitter",self.close)]:a=QAction(label,self);a.triggered.connect(fn);fm.addAction(a)
        tools=mb.addMenu("Outils"); a=QAction("Modifier la mise en page",self);a.triggered.connect(self.edit_layout);tools.addAction(a); a=QAction("Réinitialiser la mise en page",self);a.triggered.connect(self.reset_layout);tools.addAction(a)
        settings=QAction("Paramètres",self);settings.triggered.connect(self.settings);mb.addAction(settings)
        splitter=QSplitter(Qt.Horizontal)
        splitter.addWidget(self.input_panel())
        self.preview=InvoicePreview()
        preview_wrap=QWidget(); pv=QVBoxLayout(preview_wrap); pv.setContentsMargins(0,0,0,0)
        zoom_row=QHBoxLayout(); zoom_row.addWidget(QLabel("Zoom :"))
        self.zoom=QComboBox(); self.zoom.addItems(["75 %","100 %","125 %","150 %"]); self.zoom.setCurrentText("100 %")
        self.zoom.currentTextChanged.connect(lambda t:self.preview.set_zoom(float(t.replace("%","").strip())/100))
        fit=QPushButton("Ajuster à la page"); fit.clicked.connect(lambda:self.preview.set_zoom(1.0))
        zoom_row.addWidget(self.zoom); zoom_row.addWidget(fit); zoom_row.addStretch()
        pv.addLayout(zoom_row); pv.addWidget(self.preview,1)
        splitter.addWidget(preview_wrap); splitter.setSizes([520,1130]); self.setCentralWidget(splitter)
    def input_panel(self):
        root=QWidget(); out=QVBoxLayout(root); scroll=QScrollArea(); scroll.setWidgetResizable(True); body=QWidget(); lay=QVBoxLayout(body)
        box=QGroupBox("Données de la facture"); f=QFormLayout(box)
        self.species=QComboBox(); self.species.addItems(SPECIES); f.addRow("Espèce",self.species)
        self.date=QLineEdit(today_text()); self.date.setPlaceholderText("JJ/MM/AAAA"); f.addRow("Date",self.date)
        self.producer=QComboBox(); self.producer.setEditable(True); f.addRow("Nom du producteur",self.producer)
        self.address=QLineEdit(); f.addRow("Adresse",self.address); self.idcard=QLineEdit(); f.addRow("N° carte d’identité",self.idcard)
        self.agreer=QLineEdit(); f.addRow("Nom de l’agréeur",self.agreer); self.quantity=QLineEdit(); self.quantity.setPlaceholderText("0,00"); f.addRow("Quantité (Qx)",self.quantity)
        self.point=QLineEdit(); f.addRow("Point de collecte",self.point); self.bon=QLineEdit(); self.bon.setPlaceholderText("Automatique"); f.addRow("N° Bon d’entrée",self.bon)
        self.status=QComboBox(); self.status.addItems(["ACCEPTED","REFUSED"]); f.addRow("Décision",self.status)
        self.reason=QComboBox(); self.reason.setEditable(True); f.addRow("Cause du refus",self.reason)
        lay.addWidget(box); self.analysis=QGroupBox("Analyses — entrer les Valeurs uniquement"); self.af=QGridLayout(self.analysis); self.af.setColumnStretch(0,4); self.af.setColumnStretch(1,2); self.af.setColumnStretch(2,1); self.af.setColumnStretch(3,2); lay.addWidget(self.analysis)
        summary=QGroupBox("Résumé automatique")
        sf=QGridLayout(summary)
        self.bonus_label=QLabel("0,00 DA"); self.ref_label=QLabel("0,00 DA"); self.decision_label=QLabel("ACCEPTÉ")
        self.bonus_label.setStyleSheet("font-size:14pt;font-weight:700;"); self.ref_label.setStyleSheet("font-size:14pt;font-weight:700;")
        self.decision_label.setStyleSheet("font-size:12pt;font-weight:700;padding:5px;border:1px solid #999;border-radius:4px;")
        sf.addWidget(QLabel("Bonification totale"),0,0); sf.addWidget(self.bonus_label,0,1)
        sf.addWidget(QLabel("Réfaction totale"),0,2); sf.addWidget(self.ref_label,0,3)
        sf.addWidget(QLabel("État"),1,0); sf.addWidget(self.decision_label,1,1,1,3)
        lay.addWidget(summary)
        self.notice=QLabel(); self.notice.setWordWrap(True); self.notice.setStyleSheet("padding:7px;border:1px solid #bbb;background:#f5f5f5;"); lay.addWidget(self.notice)
        row=QHBoxLayout(); reset=QPushButton("Réinitialiser"); save=QPushButton("Enregistrer"); pdf=QPushButton("Exporter PDF"); hist=QPushButton("Historique")
        for b,fn in [(reset,self.reset_analysis),(save,self.save_invoice),(pdf,self.export_pdf),(hist,self.history)]:b.clicked.connect(fn);row.addWidget(b)
        lay.addLayout(row); lay.addStretch(); scroll.setWidget(body); out.addWidget(scroll)
        self.species.currentTextChanged.connect(self.rebuild_analysis); self.producer.currentTextChanged.connect(self.producer_changed); self.status.currentTextChanged.connect(self.changed); self.reason.currentTextChanged.connect(self.changed)
        return root
    def rebuild_analysis(self,*_):
        while self.af.count():
            item=self.af.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self.analysis_fields={}
        headers=("Paramètre","Valeur","Unité","Valeur de référence / Limite")
        for col,h in enumerate(headers):
            lab=QLabel(h); lab.setStyleSheet("font-weight:600; padding:4px;")
            self.af.addWidget(lab,0,col)
        for row,r in enumerate(RULES[self.species.currentText()],1):
            lab=QLabel(r.label); lab.setWordWrap(True); self.af.addWidget(lab,row,0)
            e=QLineEdit(); e.setPlaceholderText("0,00"); e.setAlignment(Qt.AlignCenter); e.setMinimumWidth(82)
            e.textChanged.connect(self.changed); e.editingFinished.connect(lambda e=e:self.normalize_analysis(e))
            self.analysis_fields[r.key]=e; self.af.addWidget(e,row,1)
            unit=QLabel(r.unit); unit.setAlignment(Qt.AlignCenter); self.af.addWidget(unit,row,2)
            ref=QLabel(r.reference); ref.setAlignment(Qt.AlignCenter); ref.setStyleSheet("color:#555;")
            self.af.addWidget(ref,row,3)
        self.update_preview()

    def normalize_analysis(self,e):
        v=num(e.text())
        if v is not None:e.setText(fmt(v))
    def producer_changed(self,*_):
        name=self.producer.currentText()
        for r in self.db.producers():
            if r["name"]==name:self.address.setText(r["address"] or "");self.idcard.setText(r["identity_number"] or "");break
        self.changed()
    def changed(self,*_):
        self.update_preview()
        if hasattr(self,"draft_timer"): self.draft_timer.start(800)
    def collect(self):
        vals={k:e.text() for k,e in self.analysis_fields.items()}
        vals["notice_title"]=self.preview.fields.get("notice_title").text() if self.preview.fields.get("notice_title") else ""
        vals["notice_reason"]=self.preview.fields.get("notice_reason").text() if self.preview.fields.get("notice_reason") else ""
        raw_bon=(self.bon.text() or "").strip()
        try: bon=int(raw_bon) if raw_bon else self.db.next_bon()
        except ValueError: bon=self.db.next_bon()
        return {"species":self.species.currentText(),"date":self.date.text().strip(),
                "producer":self.producer.currentText(),"address":self.address.text(),"producer_id":self.idcard.text(),
                "agreer":self.agreer.text(),"quantity_qx":num(self.quantity.text()),"point":self.point.text(),
                "bon_number":bon,"status":self.status.currentText(),"reason":self.reason.currentText(),
                "values":vals,"layout":self.preview.layout_json()}
    def update_preview(self):
        if not hasattr(self,"analysis_fields"):return
        d=self.collect() if self.bon.text() else {"species":self.species.currentText(),"values":{}}
        res=calculate(d["species"],d.get("values",{})); self.preview.set_data(d,res)
        self.bonus_label.setText(fmt(res.bonus)+" DA")
        self.ref_label.setText(fmt(res.refaction)+" DA")
        if self.status.currentText()=="REFUSED":
            self.decision_label.setText("PRODUIT REFUSÉ"); self.decision_label.setStyleSheet("font-size:12pt;font-weight:700;padding:5px;border:1px solid #888;border-radius:4px;")
        elif res.price_to_discuss:
            self.decision_label.setText("PRIX À DÉBATTRE"); self.decision_label.setStyleSheet("font-size:12pt;font-weight:700;padding:5px;border:1px solid #888;border-radius:4px;")
        else:
            self.decision_label.setText("ACCEPTÉ"); self.decision_label.setStyleSheet("font-size:12pt;font-weight:700;padding:5px;border:1px solid #888;border-radius:4px;")
        self.notice.setText(("PRIX À DÉBATTRE" if res.price_to_discuss else "")+((" — "+res.observation) if res.observation else ""))
    def new_invoice(self,clear_draft=True):
        if clear_draft: self.remove_draft()
        self.invoice_id=None; self.species.setCurrentText("Blé Dur"); self.rebuild_analysis(); self.date.setText(QDate.currentDate().toString("dd/MM/yyyy"))
        self.bon.setText(str(self.db.next_bon())); self.producer.setCurrentText(""); self.address.clear(); self.idcard.clear(); self.agreer.setText(self.db.setting("agreer","")); self.quantity.clear(); self.point.setText(self.db.setting("collection_point","")); self.status.setCurrentText("ACCEPTED"); self.reason.clear(); self.preview.reset_layout(); self.preview.set_data(self.collect(),calculate(self.species.currentText(),{}))
        self.preview.set_zoom(1.0)
    def load_producers(self):
        self.producer.blockSignals(True); self.producer.clear(); self.producer.addItem("")
        for r in self.db.producers(): self.producer.addItem(r["name"])
        self.producer.blockSignals(False)
    def load_reasons(self):
        self.reason.clear(); self.reason.addItems(self.db.reasons("REFUSED"))
    def revert_saved(self):
        if not self.last_saved:
            QMessageBox.information(self,"Annuler","Aucune version enregistrée à restaurer."); return
        d=self.last_saved; self.species.setCurrentText(d["species"]); self.producer.setCurrentText(d["producer"]); self.address.setText(d["address"]); self.idcard.setText(d["producer_id"]); self.agreer.setText(d["agreer"]); self.quantity.setText(fmt(d["quantity_qx"])); self.point.setText(d["point"]); self.bon.setText(str(d["bon_number"])); self.status.setCurrentText(d["status"]); self.reason.setCurrentText(d["reason"]);
        for k,e in self.analysis_fields.items(): e.setText(str(d["values"].get(k,"")))
        self.update_preview()
    def reset_analysis(self):
        if QMessageBox.question(self,"Confirmation","Voulez-vous vraiment réinitialiser les valeurs d’analyse ?",QMessageBox.Yes|QMessageBox.No)!=QMessageBox.Yes:return
        for e in self.analysis_fields.values():e.clear()
    def save_invoice(self):
        d=self.collect()
        if not d["producer"].strip():QMessageBox.warning(self,"Validation","Veuillez saisir le nom du producteur.");return
        try:
            self.invoice_id=self.db.save_invoice(d,self.invoice_id); self.db.save_producer(d["producer"],d["address"],d["producer_id"]);
            if d["status"]=="REFUSED" and d["reason"].strip(): self.db.add_reason("REFUSED",d["reason"]); self.load_producers(); self.load_reasons()
            self.last_saved=json.loads(json.dumps(d,ensure_ascii=False))
            self.remove_draft()
            QMessageBox.information(self,"Enregistrer","Facture enregistrée avec succès.")
        except sqlite3.IntegrityError: QMessageBox.warning(self,"N° Bon","Ce N° Bon existe déjà.")
    def load_invoice(self,i,duplicate=False):
        d=self.db.get_invoice(i)
        if not d:return
        self.invoice_id=None if duplicate else d["id"]; self.species.setCurrentText(d["species"]); self.date.setText(d["invoice_date"] or ""); self.producer.setCurrentText(d["producer"] or ""); self.address.setText(d["address"] or ""); self.idcard.setText(d["producer_id"] or ""); self.agreer.setText(d["agreer"] or ""); self.quantity.setText(fmt(d["quantity_qx"])); self.point.setText(d["collection_point"] or ""); self.bon.setText(str(self.db.next_bon() if duplicate else d["bon_number"])); self.status.setCurrentText(d["status"]); self.reason.setCurrentText(d["reason"] or "")
        for k,e in self.analysis_fields.items():e.setText(str(d["values"].get(k,"")))
        self.preview.edits=d.get("layout",{}); self.update_preview()
        self.preview.set_zoom(1.0)
    def history(self):
        h=HistoryDialog(self.db,self)
        if h.exec()==QDialog.Accepted and h.selected:self.load_invoice(h.selected[1],h.selected[0]=="duplicate")
    def edit_layout(self):
        self.preview.set_edit_mode(True); old=dict(self.preview.edits); d=LayoutDialog(self.preview,self); result=d.exec();
        if result==QDialog.Rejected:self.preview.edits=old; self.preview.rebuild_fields()
        else:
            if self.invoice_id:self.save_invoice()
        self.preview.set_edit_mode(False); self.update_preview()
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
        if not self.invoice_id or not self.producer.currentText().strip(): return
        try: self.invoice_id=self.db.save_invoice(self.collect(),self.invoice_id)
        except Exception: pass

    def draft_path(self):
        return ROOT/"draft.json"

    def write_draft(self):
        try:
            d=self.collect()
            if not self.invoice_id and not d["producer"].strip() and not any(str(v).strip() for v in d["values"].values()):
                return
            self.draft_path().write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8")
        except Exception: pass

    def remove_draft(self):
        try:self.draft_path().unlink(missing_ok=True)
        except Exception:pass

    def recover_draft(self):
        p=self.draft_path()
        if not p.exists(): return
        try:
            d=json.loads(p.read_text(encoding="utf-8"))
            if QMessageBox.question(self,"Récupération","Une facture non enregistrée a été récupérée.\n\nRestaurer cette facture ?",QMessageBox.Yes|QMessageBox.No)==QMessageBox.Yes:
                self.invoice_id=None
                self.species.setCurrentText(d.get("species","Blé Dur"))
                self.date.setText(d.get("date",""))
                self.producer.setCurrentText(d.get("producer","")); self.address.setText(d.get("address","")); self.idcard.setText(d.get("producer_id",""))
                self.agreer.setText(d.get("agreer","")); self.quantity.setText(fmt(d.get("quantity_qx"))); self.point.setText(d.get("point","")); self.bon.setText(str(d.get("bon_number",self.db.next_bon())))
                self.status.setCurrentText(d.get("status","ACCEPTED")); self.reason.setCurrentText(d.get("reason",""))
                for k,e in self.analysis_fields.items(): e.setText(str(d.get("values",{}).get(k,"")))
                self.preview.edits=d.get("layout",{}); self.update_preview()
            self.remove_draft()
        except Exception:
            self.remove_draft()
    def closeEvent(self,e):
        try:
            if self.db.setting("close_backup","1")=="1":
                p=Path(self.db.setting("backup_folder",str(BACKUP_ROOT)))/f"BulletinBackup_{date.today().isoformat()}_fermeture.backup"; self.db.backup(p)
        finally:self.db.close();e.accept()

def main():
    from PySide6.QtWidgets import QApplication
    app=QApplication(sys.argv); app.setStyle("Fusion"); renderer.ensure_qt_font(); app.setFont(QFont(renderer.UI_FONT,10))
    app.setStyleSheet("""
        QWidget { font-size: 10pt; }
        QGroupBox { font-weight: 600; border: 1px solid #b9b9b9; border-radius: 5px; margin-top: 10px; padding-top: 8px; }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
        QLineEdit, QComboBox { min-height: 30px; padding: 3px 7px; border: 1px solid #b7b7b7; border-radius: 4px; background: white; }
        QLineEdit:focus, QComboBox:focus { border: 1px solid #555; }
        QPushButton { min-height: 30px; padding: 4px 12px; }
        QTableWidget { background: white; }
    """)
    w=MainWindow(); w.show(); sys.exit(app.exec())

if __name__=="__main__":main()
