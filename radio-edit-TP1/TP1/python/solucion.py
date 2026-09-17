#!/usr/bin/env python3
"""Port a Python de source/Solucion.cpp.

Ver la nota sobre la convencion de indexacion en instancia.py: los pulsos se
guardan 1-based, asi que imprimir() y guardar() los emiten tal cual.
"""

import sys


class Solucion:
    def __init__(self):
        self._indices = []

    def agregar(self, pulso):
        # Agregamos el indice del pulso al final de _indices
        self._indices.append(pulso)

    def limpiar(self):
        # Borramos toda la lista _indices
        self._indices.clear()

    def indices(self):
        # Devolvemos _indices, que contiene los indices con la solucion optima
        return self._indices

    def cantidad(self):
        # Devolvemos el tamano de _indices, que deberia coincidir con k
        return len(self._indices)

    def copiar(self):
        # DIFERENCIA CON C++, y es LA diferencia de este port.
        #
        # En C++ `Solucion` se pasa POR VALOR a fb() y bt(), asi que cada
        # llamada recibe su propia copia y puede mutarla sin afectar al
        # llamador: el copy-constructor lo hace solo y no se ve en el codigo.
        # En Python los objetos viajan por referencia, asi que ese mismo codigo
        # compartiria una unica Solucion entre todos los nodos del arbol.
        #
        # Este metodo NO existe en la clase base del enunciado: es un agregado.
        # Agregar metodos esta permitido; lo que no se puede es cambiar la firma
        # de los que ya estaban, y ninguno se toco.
        nueva = Solucion()
        nueva._indices = list(self._indices)
        return nueva

    def costo(self, instancia):
        # Inicializamos el costo_total en 0.0
        costo_total = 0.0

        # Recorremos _indices y vamos sumando los costos entre dos pulsos
        # adyacentes usando sus indices.
        #
        # ARREGLADO (en el C++): la condicion era "i < _indices.size()-1". Como
        # size() devuelve un unsigned, con la solucion vacia size()-1 no daba -1
        # sino 18446744073709551615, el while entraba igual y leia fuera del
        # vector (segfault confirmado con AddressSanitizer).
        #
        # DIFERENCIA CON C++: en Python este bug es imposible. len() devuelve un
        # int con signo, asi que len([]) - 1 da -1 y el while directamente no
        # entra. Es un ejemplo concreto para el informe de una familia de
        # errores que el lenguaje elimina de raiz.
        i = 0
        while i < self.cantidad() - 1:
            costo_total += instancia.costo(self._indices[i], self._indices[i + 1])
            i += 1
        return costo_total

    def esValida(self, instancia):
        # Para que sea considerada una solucion valida debe cumplir:
        # - El tamano de la solucion debe ser exactamente k
        # - El primer pulso y el ultimo deben mantenerse
        # - Los indices en _indices deben estar estrictamente ordenados

        # ARREGLADO (en el C++): sin esto, una solucion vacia pasaba el primer if
        # cuando k tambien era 0 y reventaba en _indices[0].
        if not self._indices:
            return False

        # Tiene tamano k la solucion
        if self.cantidad() != instancia.k():
            return False

        # El primer indice siempre es 1
        if self._indices[0] != 1:
            return False

        # El ultimo pulso de la instancia original debe mantenerse
        if self._indices[self.cantidad() - 1] != instancia.n():
            return False

        for i in range(self.cantidad() - 1):
            if self._indices[i] >= self._indices[i + 1]:
                return False

        # Si cumple todas estas condiciones, devuelve True
        return True

    def imprimir(self, instancia):
        # Imprime la solucion (los indices)
        print("Seleccion: " + " ".join(str(x) for x in self._indices))
        # Imprime el costo total de la solucion
        #
        # ARREGLADO (en el C++): sin setprecision(10) salian 6 digitos
        # significativos, que no alcanzan para distinguir dos costos parecidos
        # en la experimentacion. El equivalente de setprecision(10) sobre el
        # formato por defecto de C++ es el especificador .10g de Python.
        print("Costo: " + format(self.costo(instancia), ".10g"))

    def guardar(self, ruta):
        # Escribe la seleccion de indices (solucion) en un archivo de texto, en
        # la ruta que se pasa como parametro. Es el formato que pide el
        # enunciado: una unica linea con los k enteros indexados desde 1, y es
        # lo que consume reconstruir.py.
        try:
            with open(ruta, "w") as archivo:
                archivo.write(" ".join(str(x) for x in self._indices) + "\n")
        except OSError:
            print("Atencion: no se pudo escribir el archivo de salida " + ruta,
                  file=sys.stderr)
