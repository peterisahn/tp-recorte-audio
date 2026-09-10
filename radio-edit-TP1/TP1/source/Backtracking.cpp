// #include "Backtracking.h"

// Solucion Backtracking::resolver(const Instancia& instancia) {
//     (void)instancia;
//     return Solucion();
// }

// Solucion bt (const Instancia& instancia, Solucion solucion_actual, Solucion solucion_mejor, int k, int i) {

//     // (Para cada poda devolvemos la mejor solución encontrada para que no siga explorando innecesariamente)
//     // Poda por optimalidad: Si si ya igualamos o superamos la mejor solución conocida,
//     // seguir agregando pulsos no puede mejorar el resultado
//     if (solucion_actual.costo(instancia)>= solucion_mejor.costo(instancia)) {
//         return solucion_mejor; 
//     }

//     // Poda por factibilidad: Si alcanzan los pulsos que quedan (desde i hasta n-1) para completar la cantidad de pulsos totales k
//     int faltan = k - 1 - solucion_actual.cantidad();   // cuántos más hay que elegir, sin contar el último
//     int disponibles = instancia.n() - i;       // candidatos que quedan
//     // Comparamos la cantidad de pulsos que faltan con los disponibles
//     if (faltan > disponibles) {
//         return solucion_mejor;
//     }

//     // Caso base: la solucion_actual tiene k-1 pulsos. El último pulso tiene que ser n, como en el original
//     if (solucion_actual.cantidad() == k-1) {
//         // Agregamos el último pulso
//         solucion_actual.agregar(instancia.n());

//         // Si solucion_mejor estaba vacía, devolvemos solucion_actual
//         if (solucion_mejor.cantidad() == 0){
//             return solucion_actual;
//         }

//         // Comparamos si el costo de la solución actual es menor que la mejor solución encontrada hasta el momento
//         if (solucion_actual.costo(instancia) < solucion_mejor.costo(instancia)){
//             // Actualizamos solucion_mejor
//             solucion_mejor = solucion_actual;
//         }
//         return solucion_mejor;
//     }

//     // Caso base: no quedan pulsos intermedios para probar
//     if (i>=instancia.n()){
//         return solucion_mejor;
//     }

//     // Paso recursivo:
//     // Para cada nodo del árbol recursivo hay 2 opciones: agregar/ no agregar el iésimo pulso 
//     Solucion agregar_pulso_i = solucion_actual; //Creamos una solución parcial donde agregamos el pulso i. Solucion_actual se mantiene igual
//     agregar_pulso_i.agregar(i);
//     solucion_mejor = bt(instancia, agregar_pulso_i, solucion_mejor, k, i+1); //Exploramos la rama que contiene el pulso i
//     solucion_mejor = bt(instancia, solucion_actual, solucion_mejor, k, i+1); //Exploramos la rama que no contiene el pulso i
   
//     return solucion_mejor;
// }

// Solucion Backtracking::resolver(const Instancia& instancia) {
//     // Inicalizamos las variables globales que vamos a usar en la recursión
//     Solucion solucion_actual; 
//     Solucion solucion_mejor;

//     // Agregamos el primer pulso, ya que debe mantenerse como en el original
//     solucion_actual.agregar(1);
//     // Creamos la variable entera k, que va a ser pasada como parámetro de la función pd
//     int k = instancia.k();
//     // Empezamos a recorrer el algoritmo de Fuerza Bruta desde el índice 2
//     int i = 2;

//     // Llamamos una función auxiliar que resuelve el problema usando fb
//     solucion_mejor = bt (instancia, solucion_actual, solucion_mejor, k, i);
    
//     return solucion_mejor;
// }

#include "Backtracking.h"

Solucion bt(const Instancia& instancia, Solucion solucion_actual, Solucion solucion_mejor, int k, int i) {

    // Ya elegimos k-1 pulsos.
    // El último pulso debe ser obligatoriamente n-1.
    if (solucion_actual.cantidad() == k - 1) {

        solucion_actual.agregar(instancia.n());

        // Si todavía no encontramos ninguna solución, esta pasa a ser la mejor.
        if (solucion_mejor.cantidad() == 0) {
            return solucion_actual;
        }
        // Comparamos los costos.
        if (solucion_actual.costo(instancia) < solucion_mejor.costo(instancia)) {
            solucion_mejor = solucion_actual;
        }
        return solucion_mejor;
    }
    // Poda por Factibilidad: Ya elegimos demasiados pulsos y todavía falta agregar obligatoriamente el último.
    if (solucion_actual.cantidad() >= k) {
        return solucion_mejor;
    }
    // Poda por Factibilidad: Vemos si quedan suficientes pulsos intermedios para poder llegar a una solución de tamaño k.
    int faltan_elegir = k - solucion_actual.cantidad() - 1;
    int disponibles = instancia.n() - i;
    if (faltan_elegir > disponibles) {
        return solucion_mejor;
    }
    // Poda por Optimalidad: Si ya existe una solución completa y el costo parcial actual ya es igual o mayor, esta rama nunca podrá mejorarla.
    if (solucion_mejor.cantidad() != 0 && solucion_actual.costo(instancia) >= solucion_mejor.costo(instancia)) {
        return solucion_mejor;
    }

    // Ya no quedan pulsos intermedios para probar.
    if (i >= instancia.n()) {
        return solucion_mejor;
    }
    // Opción 1: agregar el pulso i.
    Solucion agregar_pulso_i = solucion_actual;
    agregar_pulso_i.agregar(i);
    solucion_mejor = bt(instancia, agregar_pulso_i, solucion_mejor, k, i + 1);
    // Opción 2: no agregar el pulso i.
    solucion_mejor = bt(instancia, solucion_actual, solucion_mejor, k, i + 1);
    return solucion_mejor;
}

Solucion Backtracking::resolver(const Instancia& instancia) {
    Solucion solucion_actual;
    Solucion solucion_mejor;
    int k = instancia.k();
    // El primer pulso siempre debe estar.
    solucion_actual.agregar(1);
    // Empezamos a decidir desde el segundo pulso (índice 1).
    int i = 2;
    solucion_mejor = bt(instancia, solucion_actual, solucion_mejor, k, i);
    return solucion_mejor;
}
