#include "Backtracking.h"

Solucion bt(const Instancia& instancia, Solucion solucion_actual, Solucion solucion_mejor, int k, int i) {

    // Ya elegimos k-1 pulsos (El último pulso debe ser necesariamente n-1)
    if (solucion_actual.cantidad() == k - 1) {

        solucion_actual.agregar(instancia.n());

        // Si todavía no encontramos ninguna solución, esta pasa a ser la mejor
        if (solucion_mejor.cantidad() == 0) {
            return solucion_actual;
        }
        // Comparamos los costos
        if (solucion_actual.costo(instancia) < solucion_mejor.costo(instancia)) {
            solucion_mejor = solucion_actual;
        }
        return solucion_mejor;
    }
    // Poda por Factibilidad: Ya elegimos demasiados pulsos y todavía falta agregar obligatoriamente el último
    if (solucion_actual.cantidad() >= k) {
        return solucion_mejor;
    }
    // Poda por Factibilidad: Vemos si quedan suficientes pulsos intermedios para poder llegar a una solución de tamaño k
    int faltan_elegir = k - solucion_actual.cantidad() - 1;
    int disponibles = instancia.n() - i;
    if (faltan_elegir > disponibles) {
        return solucion_mejor;
    }
    // Poda por Optimalidad: Si ya existe una solución completa y el costo parcial actual ya es igual o mayor, esta rama nunca podrá mejorarla
    if (solucion_mejor.cantidad() != 0 && solucion_actual.costo(instancia) >= solucion_mejor.costo(instancia)) {
        return solucion_mejor;
    }

    // Ya no quedan pulsos intermedios para probar
    if (i >= instancia.n()) {
        return solucion_mejor;
    }
    // Opción 1: agregamos el pulso i
    Solucion agregar_pulso_i = solucion_actual;
    agregar_pulso_i.agregar(i);
    solucion_mejor = bt(instancia, agregar_pulso_i, solucion_mejor, k, i + 1);
    // Opción 2: no agregamos el pulso i
    solucion_mejor = bt(instancia, solucion_actual, solucion_mejor, k, i + 1);
    return solucion_mejor;
}

Solucion Backtracking::resolver(const Instancia& instancia) {
    Solucion solucion_actual;
    Solucion solucion_mejor;
    int k = instancia.k();
    // El primer pulso siempre debe estar.
    solucion_actual.agregar(1);
    // Empezamos a decidir desde el segundo pulso (índice 2).
    int i = 2;
    solucion_mejor = bt(instancia, solucion_actual, solucion_mejor, k, i);
    return solucion_mejor;
}
