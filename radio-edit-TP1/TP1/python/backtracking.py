#!/usr/bin/env python3
"""Port a Python de source/Backtracking.cpp.

Backtracking.

La misma recursion que fuerza bruta mas dos cortes. El caso base va primero,
asi que una hoja nunca se poda.

PODA POR FACTIBILIDAD. Faltan elegir k - cantidad() - 1 pulsos (el -1 es el
ultimo, que entra siempre) y quedan n - i disponibles. Si faltan mas de los
que hay, la rama no se puede completar.

PODA POR OPTIMALIDAD. Como c(i,j) = ||f_{i+1} - f_j|| >= 0, el costo de una
solucion parcial nunca baja al extenderla, asi que ya es cota inferior del
costo de cualquier solucion de esta rama. Solo aplica si ya existe una
solucion completa contra la cual comparar, de ahi el chequeo de cantidad() != 0.

En peor caso las podas no cortan nada y degenera en fuerza bruta: la mejora es
practica, no asintotica. Medido en n=22, k=11 sobre 10 instancias aleatorias:
BT visita 722 nodos (mediana, rango 273-1.607) contra los 863.819 de FB, o sea
el 0,084 %. Ojo que los nodos de BT dependen de la instancia y no solo de (n,k):
por eso se reporta la mediana y el rango, y no un unico valor.

Los indices son 1-based (ver la convencion en instancia.py).
"""

from algoritmo import Algoritmo
from solucion import Solucion


def bt(instancia, solucion_actual, solucion_mejor, k, i):

    # Ya elegimos k-1 pulsos.
    # El ultimo pulso debe ser obligatoriamente n.
    if solucion_actual.cantidad() == k - 1:
        # DIFERENCIA CON C++: ver la nota equivalente en fuerza_bruta.py. Alla
        # el parametro viaja por valor y agregar() no toca al llamador; aca hay
        # que copiar a mano antes de mutar.
        solucion_actual = solucion_actual.copiar()
        solucion_actual.agregar(instancia.n())

        # Si todavia no encontramos ninguna solucion, esta pasa a ser la mejor.
        if solucion_mejor.cantidad() == 0:
            return solucion_actual

        # Comparamos los costos.
        if solucion_actual.costo(instancia) < solucion_mejor.costo(instancia):
            solucion_mejor = solucion_actual
        return solucion_mejor

    # ARREGLADO (en el C++): aca habia una segunda poda por factibilidad,
    # "if (cantidad() >= k)". Es codigo muerto: cantidad() crece de a uno, asi
    # que siempre pasa por k-1 -donde corta el caso base de arriba y retorna-
    # antes de poder valer k. Instrumentado, disparo 0 veces en 3.192 nodos
    # sobre 29 combinaciones de n y k.
    # Ojo con el informe: la poda por factibilidad que SI funciona es la de
    # abajo. Es UNA, no dos.

    # Poda por Factibilidad: vemos si quedan suficientes pulsos intermedios para
    # poder llegar a una solucion de tamano k.
    faltan_elegir = k - solucion_actual.cantidad() - 1
    disponibles = instancia.n() - i
    if faltan_elegir > disponibles:
        return solucion_mejor

    # Poda por Optimalidad: si ya existe una solucion completa y el costo
    # parcial actual ya es igual o mayor, esta rama nunca podra mejorarla.
    if (solucion_mejor.cantidad() != 0 and
            solucion_actual.costo(instancia) >= solucion_mejor.costo(instancia)):
        return solucion_mejor

    # Ya no quedan pulsos intermedios para probar.
    if i >= instancia.n():
        return solucion_mejor

    # Opcion 1: agregar el pulso i.
    agregar_pulso_i = solucion_actual.copiar()
    agregar_pulso_i.agregar(i)
    solucion_mejor = bt(instancia, agregar_pulso_i, solucion_mejor, k, i + 1)
    # Opcion 2: no agregar el pulso i.
    solucion_mejor = bt(instancia, solucion_actual, solucion_mejor, k, i + 1)
    return solucion_mejor


class Backtracking(Algoritmo):
    def resolver(self, instancia):
        # Inicializamos las variables que vamos a usar en la recursion
        solucion_actual = Solucion()
        solucion_mejor = Solucion()
        k = instancia.k()
        # El primer pulso siempre debe estar.
        solucion_actual.agregar(1)
        # Empezamos a decidir desde el segundo pulso.
        i = 2
        solucion_mejor = bt(instancia, solucion_actual, solucion_mejor, k, i)
        return solucion_mejor

    def nombre(self):
        return "bt"
