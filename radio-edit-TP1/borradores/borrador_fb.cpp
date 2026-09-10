#include "FuerzaBruta.h"

Solucion fb(const Instancia& instancia, Solucion solucion_actual, Solucion solucion_mejor, int k, int i) {

    // Caso base: la solucion_actual tiene k-1 pulsos. El último pulso tiene que ser n, como en el original
    if (solucion_actual.cantidad() == k-1) {
        // Agregamos el último pulso
        solucion_actual.agregar(instancia.n());

        // Si solucion_mejor estaba vacía, devolvemos solucion_actual
        if (solucion_mejor.cantidad() == 0){
            return solucion_actual;
        }

        // Comparamos si el costo de la solución actual es menor que la mejor solución encontrada hasta el momento
        if (solucion_actual.costo(instancia) < solucion_mejor.costo(instancia)){
            // Actualizamos solucion_mejor
            solucion_mejor = solucion_actual;
        }
        return solucion_mejor;
    }

    // Caso base: no quedan pulsos intermedios para probar
    if (i>=instancia.n()){
        return solucion_mejor;
    }


    // Paso recursivo:
    // Para cada nodo del árbol recursivo hay 2 opciones: agregar/ no agregar el iésimo pulso 
    Solucion agregar_pulso_i = solucion_actual; //Creamos una solución parcial donde agregamos el pulso i. Solucion_actual se mantiene igual
    agregar_pulso_i.agregar(i);
    solucion_mejor = fb(instancia, agregar_pulso_i, solucion_mejor, k, i+1); //Exploramos la rama que contiene el pulso i
    solucion_mejor = fb(instancia, solucion_actual, solucion_mejor, k, i+1); //Exploramos la rama que no contiene el pulso i
   
    return solucion_mejor;
}
