package com.example.bulletinagreage

import android.app.Activity
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import java.util.Locale

class MainActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        findViewById<Button>(R.id.calculer).setOnClickListener { calculer() }
        findViewById<Button>(R.id.genererPdf).setOnClickListener { PdfGenerator.generateAndOpen(this, collectForm(), calculer()) }
    }

    private fun calculer() {
        val poids = value(R.id.poidsSpecifique)
        val humidite = value(R.id.humidite)
        val ergot = value(R.id.ergot)

        val impuretes1 = (value(R.id.tamis) ?: 0.0) +
                (value(R.id.debris) ?: 0.0) +
                (value(R.id.grainesNuisibles) ?: 0.0)

        val casses = value(R.id.grainsCasses) ?: 0.0
        val boutes = value(R.id.grainsBoutes) ?: 0.0
        val impuretes2 = casses + boutes +
                (value(R.id.grainsRoux) ?: 0.0) +
                (value(R.id.grainsMouchetes) ?: 0.0) +
                (value(R.id.grainsPunaises) ?: 0.0) +
                (value(R.id.grainsPiques) ?: 0.0)

        val mitadin = value(R.id.mitadin) ?: 0.0
        val bleTendre = value(R.id.bleTendre) ?: 0.0
        val mitadinTotal = mitadin + bleTendre

        findViewById<EditText>(R.id.impur1Total).setText(format(impuretes1))
        findViewById<EditText>(R.id.impur2Total).setText(format(impuretes2))
        findViewById<EditText>(R.id.mitadinTotal).setText(format(mitadinTotal))

        val result = CalculateurBleDur.calculer(
            poidsSpecifique = poids, humidite = humidite, ergot = ergot,
            impuretes1 = impuretes1, grainsCasses = casses,
            grainsBoutes = boutes, impuretes2 = impuretes2,
            mitadin = mitadinTotal, bleTendre = bleTendre
        )

        val lines = mutableListOf<String>()
        lines += "BONIFICATION : \${format(result.bonification)} DA"
        lines += "RÉFACTION : \${format(result.refaction)} DA"
        lines += "SOLDE : \${format(result.total)} DA"
        lines += "Impuretés 1ère catégorie : \${format(impuretes1)} %"
        lines += "Impuretés 2ème catégorie : \${format(impuretes2)} %"
        lines += "Mitadin brut : \${format(mitadinTotal)} %"
        lines += "Blé tendre : \${format(bleTendre)} %"
        if (humidite != null && humidite > 17.0) lines += "⚠ Humidité > 17 %"
        if (ergot != null && ergot > 1.0) lines += "⚠ Ergot > 1 ‰"
        lines += result.notes.map { "⚠ \$it" }

        findViewById<TextView>(R.id.resultat).text = lines.joinToString("\n")
    }

    private fun value(id: Int): Double? =
        findViewById<EditText>(id).text.toString().trim().replace(',', '.').toDoubleOrNull()

    private fun format(value: Double): String =
        String.format(Locale.FRANCE, "%.3f", value)
}
