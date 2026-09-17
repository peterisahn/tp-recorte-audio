#!/usr/bin/env python3
"""Port a Python de source/FuerzaBruta.cpp.

Fuerza bruta.

Representamos una solucion como una secuencia de decisiones sobre los pulsos
intermedios: para cada uno decidimos si lo conservamos o lo descartamos.

Es generate and test: evalua TODAS las soluciones factibles y se queda con la
mejor, sin usar nunca la funcion objetivo para cortar. Verificado contando:
evalua exactamente C(n-2, k-2) selecciones (3.003 en n=16, 167.960 en n=22).
No visita los 2^(n-1)-1 nodos del arbol binario de decisiones porque enumera
combinaciones en vez de subconjuntos, que es la misma formulacion del oraculo
de oraculo.py; las dos son fuerza bruta.

Complejidad: O(2^n * k * d) en tiempo, O(n) en espacio.
Los indices son 1-based (ver la convencion en instancia.py).
"""

from algoritmo import Algoritmo
from solucion import Solucion


def fb(instancia, solucion_actual, solucion_mejor, k, i):

    # Caso base: la solucion_actual tiene k-1 pulsos. El ultimo pulso tiene que
    # ser n, como en el original.
    if solucion_actual.cantidad() == k - 1:
        # DIFERENCIA CON C++: alla solucion_actual es un parametro POR VALOR, o
        # sea una copia propia de esta llamada, y este agregar() no toca al
        # llamador. En Python el objeto viaja por referencia, asi que hay que
        # copiarlo a mano antes de mutarlo. Sin esta copia el pulso n se cuela
        # en la solucion parcial del llamador y la segunda rama explora basura.
        solucion_actual = solucion_actual.copiar()

        # Agregamos el ultimo pulso
        solucion_actual.agregar(instancia.n())

        # Si solucion_mejor estaba vacia, devolvemos solucion_actual
        if solucion_mejor.cantidad() == 0:
            return solucion_actual

        # Comparamos si el costo de la solucion actual es menor que el de la
        # mejor solucion encontrada hasta el momento
        if solucion_actual.costo(instancia) < solucion_mejor.costo(instancia):
            # Actualizamos solucion_mejor
            solucion_mejor = solucion_actual
        return solucion_mejor

    # Caso base: no quedan pulsos intermedios para probar
    if i >= instancia.n():
        return solucion_mejor

    # Paso recursivo:
    # Para cada nodo del arbol recursivo hay 2 opciones: agregar / no agregar el
    # iesimo pulso.

    # Creamos una solucion parcial donde agregamos el pulso i. solucion_actual
    # se mantiene igual: en C++ esta copia es la asignacion `Solucion
    # agregar_pulso_i = solucion_actual;`, aca es explicita.
    agregar_pulso_i = solucion_actual.copiar()
    agregar_pulso_i.agregar(i)
    # Exploramos la rama que contiene el pulso i
    solucion_mejor = fb(instancia, agregar_pulso_i, solucion_mejor, k, i + 1)
    # Exploramos la rama que no contiene el pulso i
    solucion_mejor = fb(instancia, solucion_actual, solucion_mejor, k, i + 1)
    return solucion_mejor


class FuerzaBruta(Algoritmo):
    def resolver(self, instancia):
        # Inicializamos las variables que vamos a usar en la recursion
        solucion_actual = Solucion()
        solucion_mejor = Solucion()

        # Agregamos el primer pulso, ya que debe mantenerse como en el original
        solucion_actual.agregar(1)
        # Creamos la variable entera k
        k = instancia.k()
        # Empezamos a recorrer el algoritmo de Fuerza Bruta desde el indice 2
        i = 2
        # Llamamos a la funcion auxiliar que resuelve el problema usando fb
        solucion_mejor = fb(instancia, solucion_actual, solucion_mejor, k, i)
        return solucion_mejor

    def nombre(self):
        return "fb"
