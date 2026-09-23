import sys
from datetime import date
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QApplication,QComboBox,QFormLayout,QGroupBox,QHBoxLayout,QLabel,
    QLineEdit,QMainWindow,QMessageBox,QPushButton,QScrollArea,QSplitter,
    QVBoxLayout,QWidget
)

from database import Database
from invoice_engine import RULES,SPECIES,calculate,format_number

DATA_ROOT = Path.home() / "Documents" / "Bulletin d’Agréage"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        DATA_ROOT.mkdir(parents=True, exist_ok=True)
        self.db = Database(DATA_ROOT / "bulletin.db")
        self.fields = {}
        self.analysis_fields = {}
        self.setWindowTitle("Bulletin d’Agréage")
        self.resize(1500, 950)
        self.build_ui()
        self.new_invoice()

    def build_ui(self):
        menu = self.menuBar()
        file_menu = menu.addMenu("Fichier")
        action = QAction("Nouvelle facture", self)
        action.triggered.connect(self.new_invoice)
        file_menu.addAction(action)
        settings = QAction("Paramètres", self)
        settings.triggered.connect(self.show_settings)
        menu.addAction(settings)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self.input_panel())
        splitter.addWidget(self.preview_panel())
        splitter.setSizes([520, 980])
        self.setCentralWidget(splitter)

    def input_panel(self):
        root = QWidget()
        outer = QVBoxLayout(root)
        general = QGroupBox("Données de la facture")
        form = QFormLayout(general)
        self.add_combo(form,"Espèce","species",SPECIES)
        for key,label in [
            ("date","Date"),("producer","Nom du producteur"),("address","Adresse"),
            ("producer_id","N° carte d’identité"),("agreer","Nom de l’agréeur"),
            ("quantity","Quantité (Qx)"),("point","Point de collecte"),("bon","N° Bon d’entrée")]:
            self.add_line(form,key,label)
        outer.addWidget(general)

        self.analysis_box = QGroupBox("Analyses")
        self.analysis_layout = QFormLayout(self.analysis_box)
        outer.addWidget(self.analysis_box)

        buttons = QHBoxLayout()
        reset = QPushButton("Réinitialiser")
        reset.clicked.connect(self.reset_analysis)
        save = QPushButton("Enregistrer")
        save.clicked.connect(self.save_invoice)
        buttons.addWidget(reset)
        buttons.addStretch()
        buttons.addWidget(save)
        outer.addLayout(buttons)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(root)
        wrapper = QWidget()
        lay = QVBoxLayout(wrapper)
        lay.addWidget(scroll)
        return wrapper

    def preview_panel(self):
        box = QGroupBox("Aperçu A4")
        lay = QVBoxLayout(box)
        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setStyleSheet("background:#f2f2f2;border:1px solid #aaa;")
        lay.addWidget(self.preview)
        return box

    def add_combo(self, form, label, key, values):
        combo = QComboBox()
        combo.addItems(values)
        combo.currentTextChanged.connect(lambda value,k=key:self.changed(k,value))
        self.fields[key]=combo
        form.addRow(label,combo)

    def add_line(self, form, key, label):
        edit=QLineEdit()
        edit.textChanged.connect(lambda value,k=key:self.changed(k,value))
        self.fields[key]=edit
        form.addRow(label,edit)

    def rebuild_analysis(self, species):
        while self.analysis_layout.rowCount():
            self.analysis_layout.removeRow(0)
        self.analysis_fields.clear()
        for rule in RULES[species]:
            edit=QLineEdit()
            edit.setPlaceholderText(rule.unit)
            edit.textChanged.connect(self.recalculate)
            ref=QLabel(rule.reference or "—")
            self.analysis_fields[rule.key]=edit
            self.analysis_layout.addRow(f"{rule.label} ({rule.unit})",edit)
            self.analysis_layout.addRow("Valeur de référence",ref)

    def new_invoice(self):
        self.fields["date"].setText(date.today().strftime("%d/%m/%Y"))
        self.fields["bon"].setText(str(self.db.next_bon_number()))
        self.fields["species"].setCurrentText("Blé Dur")
        self.rebuild_analysis("Blé Dur")
        self.recalculate()

    def changed(self,key,value):
        if key=="species":
            self.rebuild_analysis(value)
        self.recalculate()

    def recalculate(self):
        values={k:v.text() for k,v in self.analysis_fields.items()}
        result=calculate(self.fields["species"].currentText(),values)
        self.preview.setText(
            f"<h2>Bulletin d’Agréage</h2>"
            f"<b>Espèce:</b> {self.fields['species'].currentText()}<br>"
            f"<b>Producteur:</b> {self.fields['producer'].text()}<br>"
            f"<b>Bon:</b> {self.fields['bon'].text()}<br><br>"
            f"Bonification: {format_number(result.total_bonification)}<br>"
            f"Réfaction: {format_number(result.total_refaction)}"
        )

    def reset_analysis(self):
        if QMessageBox.question(
            self,"Confirmation",
            "Voulez-vous vraiment réinitialiser les valeurs d’analyse ?",
            QMessageBox.Yes|QMessageBox.No) != QMessageBox.Yes:
            return
        for field in self.analysis_fields.values():
            field.clear()
        self.recalculate()

    def save_invoice(self):
        QMessageBox.information(
            self,"Enregistrer",
            "Base locale initialisée. La persistance complète et le rendu A4 final seront ajoutés dans les prochaines étapes."
        )

    def show_settings(self):
        QMessageBox.information(
            self,"Paramètres",
            "Les paramètres complets seront intégrés dans la prochaine étape."
        )

    def closeEvent(self,event):
        self.db.close()
        event.accept()

def main():
    app=QApplication(sys.argv)
    app.setApplicationName("Bulletin d’Agréage")
    app.setFont(QFont("Segoe UI",10))
    window=MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__=="__main__":
    main()
