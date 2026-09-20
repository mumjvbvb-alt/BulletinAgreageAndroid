package com.example.bulletinagreage

import kotlin.math.ceil

data class RowAdjustment(
    val bonification: Double = 0.0,
    val refaction: Double = 0.0
)

data class CalculationResult(
    val bonification: Double,
    val refaction: Double,
    val total: Double,
    val notes: List<String>,
    val rows: Map<String, RowAdjustment> = emptyMap()
)

object CalculateurBleDur {
    private fun tranches(exces: Double, taille: Double): Int =
        if (exces <= 0.0) 0 else ceil(exces / taille).toInt()

    fun calculer(
        poidsSpecifique: Double?, humidite: Double?, ergot: Double?,
        impuretes1: Double?, grainsCasses: Double?, grainsBoutes: Double?,
        impuretes2: Double?, mitadin: Double?, bleTendre: Double?,
        differencePrixBleDurTendre: Double? = null
    ): CalculationResult {
        var boni = 0.0
        var refa = 0.0
        val notes = mutableListOf<String>()
        val rows = linkedMapOf<String, RowAdjustment>()

        fun add(key: String, b: Double = 0.0, r: Double = 0.0) {
            if (b != 0.0 || r != 0.0) rows[key] = RowAdjustment(b, r)
            boni += b
            refa += r
        }

        poidsSpecifique?.let { p ->
            when {
                p > 80.0 -> {
                    val n1 = tranches(minOf(p, 82.0) - 80.0, 0.25)
                    val n2 = tranches(minOf(p, 83.0) - 82.0, 0.25)
                    val n3 = tranches(minOf(p, 84.0) - 83.0, 0.25)
                    val n4 = tranches(maxOf(p - 84.0, 0.0), 0.25)
                    add("poids", n1 * 0.15 + n2 * 0.10 + (n3 + n4) * 0.05)
                }
                p < 76.0 && p >= 72.0 -> {
                    val n1 = tranches(76.0 - maxOf(p, 75.0), 0.25)
                    val n2 = tranches(75.0 - maxOf(p, 74.0), 0.25)
                    val n3 = tranches(74.0 - p, 0.25)
                    add("poids", r = n1 * 0.10 + n2 * 0.20 + n3 * 0.30)
                }
                p < 72.0 -> notes += "Poids spécifique inférieur à 72 kg/hl : hors critère sain, loyal et marchand."
            }
        }

        humidite?.let { if (it > 17.0) notes += "Humidité supérieure à 17 % : hors limite." }
        ergot?.let { if (it > 1.0) notes += "Ergot supérieur à 1 ‰ : hors limite." }

        impuretes1?.let {
            when {
                it < 1.0 -> add("impur1", b = tranches(1.0 - it, 0.25) * 0.125)
                it > 3.0 && it <= 6.0 -> add("impur1", r = tranches(it - 3.0, 0.25) * 0.125)
                it > 6.0 -> notes += "Impuretés 1ère catégorie > 6 % : prix à débattre."
            }
        }

        grainsCasses?.let {
            if (it > 5.0) add("casses", r = tranches(it - 5.0, 0.25) * 0.075)
        }
        grainsBoutes?.let {
            if (it > 5.0) add("boutes", r = tranches(it - 5.0, 1.0) * 0.05)
        }

        impuretes2?.let {
            when {
                it > 10.0 && it <= 20.0 -> add("impur2", r = tranches(it - 10.0, 1.0) * 0.50)
                it > 20.0 -> notes += "Impuretés 2ème catégorie > 20 % : hors barème."
            }
        }

        mitadin?.let {
            when {
                it in 0.0..10.0 -> add("mitadin", b = 0.25)
                it > 20.0 && it <= 70.0 -> add("mitadin", r = tranches(it - 20.0, 1.0) * 0.05)
                it > 70.0 -> notes += "Mitadin > 70 % : paiement au prix du blé tendre avec son barème."
            }
        }

        bleTendre?.let {
            when {
                it > 5.0 && it <= 10.0 -> {
                    if (differencePrixBleDurTendre != null && differencePrixBleDurTendre > 0.0) {
                        add("bleTendre", r = ((it - 5.0) / 100.0) * differencePrixBleDurTendre)
                    } else {
                        notes += "Blé tendre > 5 % : différence de prix blé dur/blé tendre nécessaire pour chiffrer la réfaction."
                    }
                }
                it > 10.0 -> notes += "Blé tendre > 10 % : paiement du blé dur au prix du blé tendre avec son barème."
            }
        }

        return CalculationResult(boni, refa, boni - refa, notes, rows)
    }
}
