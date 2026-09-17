#!/usr/bin/env python3
"""Port a Python de source/Instancia.cpp.

Se mantiene lo mas parecido posible al C++: los mismos nombres de metodos, la
misma convencion de indexacion y las mismas validaciones, para que el informe
pueda poner las dos implementaciones una al lado de la otra.

Los comentarios ARREGLADO marcan los bugs que tenia la version original del
grupo y que ya venian corregidos en el C++; se conservan porque son material
directo del informe. Los comentarios DIFERENCIA CON C++ marcan los lugares
donde Python obligo a cambiar algo, que es lo que pide el punto 3 del enunciado
al comparar implementaciones.
"""

import math

# ----------------------------------------------------------------------------
# Convencion de indexacion
#
# Los indices de pulso son 1-based: el pulso 1 del enunciado es el 1 aca, y el
# pulso n es el n. La lista _features en cambio se llena 0-based, asi que
# costo(i, j) mira _features[i] (que es el pulso i+1) contra _features[j-1]
# (que es el pulso j). Como la seleccion ya viaja 1-based, imprimir() y
# guardar() la emiten tal cual, sin convertir nada.
# ----------------------------------------------------------------------------


def _tokens(ruta):
    # DIFERENCIA CON C++: alla `archivo >> x` saltea cualquier espacio en blanco
    # y no le importa el corte de lineas. Para leer igual, aplanamos el archivo
    # a una secuencia de tokens en vez de ir linea por linea. Asi una instancia
    # con los features repartidos de otra forma se lee identico en los dos.
    with open(ruta) as archivo:
        for linea in archivo:
            for token in linea.split():
                yield token


class Instancia:
    def __init__(self, ruta=None):
        self._n = 0
        self._d = 0
        self._k = 0
        self._features = []
        if ruta is not None:
            self.cargar(ruta)

    def cargar(self, ruta):
        try:
            tokens = _tokens(ruta)
        except OSError:
            raise RuntimeError("No se pudo abrir el archivo: " + ruta)

        # ARREGLADO: antes se leia n, d y k sin mirar si la lectura habia
        # funcionado, y sin validar los valores. Con una cabecera rota quedaban
        # en 0 y el programa seguia; con k > n o n < 2 los algoritmos terminaban
        # leyendo fuera del arreglo (segfault confirmado en el C++).
        try:
            self._n = int(next(tokens))
            self._d = int(next(tokens))
            self._k = int(next(tokens))
        except (StopIteration, ValueError):
            raise RuntimeError(
                "Formato invalido: se esperaba 'n d k' en la primera linea de " + ruta)

        # Validaciones derivadas del enunciado: hacen falta al menos dos pulsos,
        # porque el primero y el ultimo se conservan siempre; por lo mismo
        # k >= 2, y no se pueden conservar mas pulsos de los que existen.
        if self._n < 2:
            raise RuntimeError("La instancia debe tener al menos 2 pulsos (n >= 2).")
        if self._d < 1:
            raise RuntimeError("Cada pulso debe tener al menos una caracteristica (d >= 1).")
        if self._k < 2 or self._k > self._n:
            raise RuntimeError("Debe cumplirse 2 <= k <= n.")

        # ARREGLADO: si se llama cargar() dos veces sobre la misma instancia, sin
        # esto los pulsos de la segunda se apilaban atras de los de la primera.
        self._features = []

        # Recorremos en un loop los n pulsos que vamos a ir llenando en
        # _features. A su vez cada pulso lo vamos llenando con sus
        # caracteristicas que correspondan.
        for _ in range(self._n):
            pulso = []
            for _ in range(self._d):
                # ARREGLADO: antes no se chequeaba la lectura, asi que un archivo
                # con features de menos se completaba con ceros en silencio.
                try:
                    pulso.append(float(next(tokens)))
                except (StopIteration, ValueError):
                    raise RuntimeError(
                        "Faltan caracteristicas en " + ruta + ": se esperaban " +
                        str(self._n * self._d) + " valores.")
            self._features.append(pulso)

    def n(self):
        return self._n

    def d(self):
        return self._d

    def k(self):
        return self._k

    def feature(self, i):
        return self._features[i]

    def costo(self, i, j):
        # Para obtener el costo de la diferencia entre ambos pulsos vamos a
        # aplicar la formula para calcular la distancia entre dos vectores.
        #
        #     c(i, j) = || f_{i+1} - f_j ||_2
        #
        # Compara lo que DEBERIA haber sonado (el pulso siguiente a i) contra lo
        # que efectivamente suena (el pulso j). Con la indexacion 1-based de
        # arriba, f_{i+1} esta en _features[i] y f_j en _features[j-1]. De ahi
        # que c(i, i+1) = 0: si no hay salto, no hay costo.
        suma = 0.0
        anterior = self._features[i]
        siguiente = self._features[j - 1]
        for m in range(self._d):
            dif = anterior[m] - siguiente[m]
            dif = dif * dif
            suma += dif
        return math.sqrt(suma)
