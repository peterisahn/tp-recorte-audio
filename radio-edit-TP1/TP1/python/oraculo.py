#!/usr/bin/env python3

import argparse
import itertools
import math

# Oraculo: fuerza bruta independiente, en Python.
#
# Su unico proposito es contrastar contra el C++. Por eso NO es un port de
# FuerzaBruta.cpp: si repitiera la misma estructura repetiria tambien los mismos
# errores, y un test que comparte los bugs del codigo que testea no verifica
# nada. Las diferencias son deliberadas:
#
#   - el C++ recorre un arbol binario de decisiones (conservar / descartar cada
#     pulso intermedio); aca se enumeran directamente los subconjuntos de tamano
#     k-2 de los pulsos intermedios con itertools.combinations;
#   - el C++ acumula el costo con su propio Instancia::costo; aca la norma la
#     calcula math.dist, de la biblioteca estandar.
#
# Enumera C(n-2, k-2) selecciones, asi que solo sirve para instancias chicas.
# Los indices son 0-based adentro y se pasan a 1-based solo al imprimir, igual
# que en el C++.


def leer_instancia(ruta):
    with open(ruta) as f:
        datos = f.read().split()

    n, d, k = int(datos[0]), int(datos[1]), int(datos[2])

    if n < 2:
        raise ValueError("La instancia debe tener al menos 2 pulsos (n >= 2).")
    if d < 1:
        raise ValueError("Cada pulso debe tener al menos una caracteristica (d >= 1).")
    if not 2 <= k <= n:
        raise ValueError("Debe cumplirse 2 <= k <= n.")
    if len(datos) < 3 + n * d:
        raise ValueError(f"Faltan caracteristicas: se esperaban {n * d} valores.")

    valores = [float(x) for x in datos[3:3 + n * d]]
    features = [valores[i * d:(i + 1) * d] for i in range(n)]
    return n, d, k, features


def costo(features, i, j):
    # c(i, j) = ||f_{i+1} - f_j||_2
    return math.dist(features[i + 1], features[j])


def costo_seleccion(features, seleccion):
    return sum(costo(features, seleccion[t], seleccion[t + 1])
               for t in range(len(seleccion) - 1))


def combinaciones(n, k):
    return math.comb(n - 2, k - 2)


def resolver(n, k, features):
    mejor_costo = math.inf
    mejor = None

    # Los pulsos 0 y n-1 se conservan siempre; se eligen los k-2 intermedios.
    for medio in itertools.combinations(range(1, n - 1), k - 2):
        seleccion = (0,) + medio + (n - 1,)
        actual = costo_seleccion(features, seleccion)
        if actual < mejor_costo:
            mejor_costo = actual
            mejor = seleccion

    return mejor_costo, list(mejor)


def resolver_archivo(ruta):
    n, d, k, features = leer_instancia(ruta)
    return resolver(n, k, features)


def main():
    parser = argparse.ArgumentParser(
        description="Fuerza bruta independiente en Python, para contrastar contra el C++.")
    parser.add_argument("instancia")
    args = parser.parse_args()

    n, d, k, features = leer_instancia(args.instancia)
    print(f"Instancia cargada: n={n} pulsos, d={d} caracteristicas, k={k} a conservar")
    print(f"Selecciones a evaluar: {combinaciones(n, k)}")

    mejor_costo, mejor = resolver(n, k, features)

    print("Seleccion:", " ".join(str(p + 1) for p in mejor))
    print(f"Costo: {mejor_costo:.10g}")


if __name__ == "__main__":
    main()
