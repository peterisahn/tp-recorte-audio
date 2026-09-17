#!/usr/bin/env python3
"""Port a Python de source/ProgramacionDinamica.cpp.

Programacion dinamica.

En el arbol de backtracking, dos ramas distintas que llegan al mismo pulso j
habiendo conservado la misma cantidad t de pulsos enfrentan el mismo
subproblema: lo que falta depende solo de (j, t) y no de como llegamos. Esa
superposicion de estados es la que habilita la PD.

  g(j, t) = costo minimo de una seleccion de t pulsos que termina en j

  g(j, 2) = c(1, j)
  g(j, t) = min sobre i < j de { g(i, t-1) + c(i, j) }

Se resuelve top-down con memoizacion, y se guarda padre(j, t) = el i que
realiza el minimo, que es lo que permite reconstruir la seleccion y no solo
su costo.

Complejidad: O(n^2 * k * d) en tiempo y O(n*k) en espacio.
Los indices son 1-based (ver la convencion en instancia.py).
"""

import math

from algoritmo import Algoritmo
from solucion import Solucion


def reconstruir_solucion_pd(padre, n, k):
    # Funcion que reconstruye la solucion. Como fuimos guardando los indices
    # ('padre') a medida que ibamos construyendo la solucion, la tarea de
    # reconstruccion es mas simple.
    indices = []
    j = n
    t = k

    while t > 1:
        indices.append(j)
        j = padre[j][t]

        # ARREGLADO (en el C++): si el padre nunca se escribio no hay seleccion
        # factible, y sin este corte la vuelta siguiente indexa padre[-1].
        #
        # DIFERENCIA CON C++: alla padre[-1] era un acceso fuera del vector, o
        # sea un segfault. En Python padre[-1] es un indice valido -el ultimo
        # elemento- asi que el mismo bug NO explota: devuelve silenciosamente
        # una seleccion equivocada. Es peor, porque no se nota. El corte hace
        # falta igual, y este contraste va al informe.
        if j < 0:
            return Solucion()

        t -= 1

    indices.append(1)   # el pulso 1 siempre es el inicio

    indices.reverse()   # los juntamos en orden inverso, hay que darlos vuelta

    solucion = Solucion()
    for indice in indices:
        solucion.agregar(indice)
    return solucion


def minimo(a, b):
    # Funcion auxiliar que devuelve el minimo entre dos costos
    if a > b:
        return b
    else:
        return a


def pd(instancia, j, t, memo, padre):
    # aclaracion: j,t son variables (indices) que representan sub-instancias del
    # problema original n,k respectivamente
    #
    # ARREGLADO (en el C++): el memo y esta funcion usaban float. Instancia.costo
    # devuelve double, asi que cada suma se truncaba, y con k en los cientos el
    # error acumulado ya se ve. Va todo en double.
    #
    # DIFERENCIA CON C++: en Python el float ES el double de C, no hay un tipo
    # de 32 bits al alcance de la mano. Este bug tampoco se puede escribir aca.

    # Casos base:
    # Si t>j: si se quiere tomar t pulsos de j pulsos totales tal que t>j, es
    # imposible. Devolvemos infinito.
    if t > j:
        return math.inf
    else:
        # Si t==2, tomamos el primer y el ultimo pulso j (con t<j)
        if t == 2:
            padre[j][2] = 1
            return instancia.costo(1, j)

    # Si ya calculamos el costo acumulado para t pulsos tomados de j pulsos
    # (t<=j), devolvemos lo que hay en el memo.
    # Idea: como existe superposicion de estados buscamos evitar calcular varias
    # veces una misma sub-instancia.
    if memo[j][t] >= 0:
        return memo[j][t]

    # Inicializamos la variable de retorno res en infinito, que almacena los
    # valores que van a ir en cada celda y finalmente en la celda de interes:
    # memo[n][k].
    res = math.inf
    # Inicializamos una variable que guarde el indice del pulso desde cuyo costo
    # hacia el siguiente sea el minimo
    guardar_pos = -1

    # Para cada i (i<j) que puede elegir de los pulsos restantes hasta la
    # posicion j (actual), usando t-1 pulsos.
    #
    # ARREGLADO (en el C++): la condicion era "i < j-1", que deja afuera al
    # predecesor i = j-1 y por lo tanto vuelve imposible elegir dos pulsos
    # consecutivos. Como c(j-1, j) = 0 (no cortar no cuesta nada), era
    # justamente el salto mas barato el que se estaba salteando: daba resultados
    # suboptimos, y cuando ningun predecesor quedaba alcanzable (por ejemplo con
    # k = n) el padre quedaba en -1 y la reconstruccion fallaba.
    # ARREGLADO (en el C++): el bucle arrancaba en i = 2. Para un estado (j,t) el
    # predecesor tiene que alojar t-1 pulsos, asi que ningun i < t-1 puede
    # servir: la recursion devuelve infinito al instante y el costo(i,j) que la
    # acompana se calcula igual. Medido en n=400, k=200: 3.880.703 de 7.880.202
    # llamadas (49 %) eran de esas. Arrancar en t-1 da 1,7x, con la misma
    # seleccion.
    for i in range(t - 1, j):
        # Guardamos en la celda el minimo entre lo que ya estaba guardado
        # (inicialmente infinito) y lo que devuelve la recursion usando t-1
        # pulsos hasta el pulso i, mas el costo de ir desde i hasta j.
        nuevo_res = minimo(res, pd(instancia, i, t - 1, memo, padre) + instancia.costo(i, j))
        if nuevo_res != res:
            # Si cambio, quiere decir que la recursion encontro una solucion mejor
            guardar_pos = i
        res = nuevo_res

    # Guardamos (y retornamos) finalmente en res el costo acumulado minimo de
    # tomar t pulsos hasta el pulso j
    memo[j][t] = res
    # Guardamos el 'padre' de la instancia j,t
    padre[j][t] = guardar_pos
    return res


class ProgramacionDinamica(Algoritmo):
    def resolver(self, instancia):
        # Inicializamos las variables enteras k,n
        k = instancia.k()
        n = instancia.n()

        # Creamos el memo de tamano (n+1, k+1) = (filas, columnas),
        # inicializando las celdas en -1.0, que quiere decir que todavia no las
        # visitamos
        memo = [[-1.0] * (k + 1) for _ in range(n + 1)]
        # Creamos una tabla que guarda quien es el 'padre' para cada instancia j,t
        padre = [[-1] * (k + 1) for _ in range(n + 1)]

        # Llamamos a la funcion auxiliar que llena el memo y la tabla de padres.
        # El costo minimo queda en memo[n][k]; el que se imprime lo recalcula
        # Solucion.costo a partir de la seleccion, asi que no hace falta guardarlo.
        pd(instancia, n, k, memo, padre)

        # Llamamos a una funcion auxiliar que reconstruye la solucion (los
        # indices) a partir de la tabla de padres
        return reconstruir_solucion_pd(padre, n, k)

    def nombre(self):
        return "pd"
