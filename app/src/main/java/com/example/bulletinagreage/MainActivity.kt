package com.example.bulletinagreage

import android.app.Activity
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView

class MainActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        val calculate = findViewById<Button>(R.id.calculer)
        val result = findViewById<TextView>(R.id.resultat)

        calculate.setOnClickListener {
            val weight = value(R.id.poidsSpecifique)
            val water = value(R.id.humidite)
            val ergot = value(R.id.ergot)

            val weightStatus = when {
                weight == null -> "Poids spécifique : non renseigné"
                weight in 76.0..80.0 -> "Poids spécifique : conforme"
                else -> "Poids spécifique : hors plage de référence"
            }

            val waterStatus = when {
                water == null -> "Teneur en eau : non renseignée"
                water <= 17.0 -> "Teneur en eau : conforme"
                else -> "Teneur en eau : hors limite"
            }

            val ergotStatus = when {
                ergot == null -> "Ergot : non renseigné"
                ergot <= 1.0 -> "Ergot : conforme"
                else -> "Ergot : hors limite"
            }

            result.text = listOf(weightStatus, waterStatus, ergotStatus).joinToString("\n")
        }
    }

    private fun value(id: Int): Double? {
        val text = findViewById<EditText>(id).text.toString().trim().replace(',', '.')
        return text.toDoubleOrNull()
    }
}
