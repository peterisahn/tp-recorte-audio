#!/usr/bin/env python3

import argparse
import csv
import math
import os
import random

# Generador de instancias para los tests y la experimentacion.
#
# Tres familias, cada una con un proposito distinto:
#
# ALEATORIAS. Cada caracteristica se sortea uniforme en [0,1), independiente de
# las demas y de los otros pulsos. No hay repeticiones, asi que practicamente
# ningun salto resulta barato: es el caso adverso para la poda por optimalidad
# de BT, y el que hay que reportar como peor caso en la experimentacion.
#
# ESTRUCTURADAS. Imitan la Figura 1 del enunciado: una secuencia de secciones
# (por ejemplo A B B C B B) donde todas las repeticiones de una misma seccion
# son identicas pulso a pulso. Son el caso de uso real y ademas tienen OPTIMO
# CONOCIDO, lo que las convierte en un test de correctitud gratis: ver
# bloques_descartables.
#
# BORDES. k=2, k=n y n=2: los extremos de la region factible. Los tres tienen
# optimo calculable a mano, asi que tambien sirven como test.
#
# Todas las instancias se generan con semilla explicita: la suite es reproducible
# y las instancias quedan versionadas en TP1/input/instancias/.
#
# Solo usa la biblioteca estandar (ver requirements.txt).


def redondear(features):
    # Las instancias se escriben con 4 decimales, asi que el C++ no lee los
    # features que generamos sino su version redondeada. Redondeamos aca, en el
    # generador, para que todo lo que calculemos en Python (empezando por el
    # optimo analitico de las estructuradas y los bordes) use exactamente los
    # mismos numeros que va a leer el algoritmo. Sin esto los costos difieren en
    # el quinto decimal y el test de optimo conocido falla por una diferencia
    # que no es del algoritmo sino del formato de archivo.
    return [[float(f"{v:.4f}") for v in vector] for vector in features]


def escribir(ruta, features, k):
    n = len(features)
    d = len(features[0])

    directorio = os.path.dirname(ruta)
    if directorio:
        os.makedirs(directorio, exist_ok=True)

    # Mismo formato que escribe extraer.py, para que las instancias sinteticas y
    # las extraidas de audio real sean indistinguibles para el C++.
    with open(ruta, "w") as f:
        f.write(f"{n} {d} {k}\n")
        for vector in features:
            f.write(" ".join(f"{v:.4f}" for v in vector) + "\n")


# ---------------------------------------------------------------------------
# Aleatorias
# ---------------------------------------------------------------------------

def aleatoria(n, d, semilla):
    rng = random.Random(semilla)
    return redondear([[rng.random() for _ in range(d)] for _ in range(n)])


# ---------------------------------------------------------------------------
# Estructuradas
# ---------------------------------------------------------------------------

def estructurada(secciones, pulsos, d, semilla, ruido=0.0):
    # Una plantilla por letra: `pulsos` vectores que se repiten identicos cada
    # vez que la seccion vuelve a aparecer. Eso es lo que hace que un estribillo
    # sea intercambiable con otro, que es la premisa del recorte consciente.
    rng = random.Random(semilla)

    plantillas = {}
    for letra in secciones:
        if letra not in plantillas:
            plantillas[letra] = [[rng.random() for _ in range(d)] for _ in range(pulsos)]

    features = []
    for letra in secciones:
        for vector in plantillas[letra]:
            if ruido > 0.0:
                features.append([v + rng.gauss(0.0, ruido) for v in vector])
            else:
                features.append(list(vector))
    return redondear(features)


def bloques_descartables(secciones):
    # Que un bloque se pueda descartar entero SIN COSTO sale de la definicion de
    # c(i,j) = ||f_{i+1} - f_j||. Si descartamos el bloque b completo, el unico
    # salto de la seleccion va del ultimo pulso del bloque b-1 al primero del
    # bloque b+1. Llamando m al largo de cada bloque, ese salto es
    #
    #     c(b*m - 1, (b+1)*m) = || f[b*m] - f[(b+1)*m] ||
    #
    # es decir: compara el PRIMER pulso del bloque descartado contra el PRIMER
    # pulso del que le sigue. Si ambos bloques son de la misma seccion esos dos
    # pulsos son identicos y el salto cuesta exactamente 0.
    #
    # El bloque 0 y el ultimo no se pueden descartar: los pulsos 1 y n siempre
    # se conservan.
    return [b for b in range(1, len(secciones) - 1) if secciones[b] == secciones[b + 1]]


def optimo_estructurada(secciones, pulsos, descartar):
    # Descartando `descartar` bloques descartables NO ADYACENTES entre si, todos
    # los saltos cuestan 0 y el resto de la seleccion son pulsos consecutivos,
    # que tambien cuestan 0. Como c(i,j) >= 0 siempre, una seleccion de costo 0
    # es necesariamente optima: no hace falta explorar nada para saberlo.
    libres = bloques_descartables(secciones)
    if descartar > len(libres):
        raise SystemExit(
            f"Se pidio descartar {descartar} bloques pero '{secciones}' solo tiene "
            f"{len(libres)} descartables: {libres}"
        )

    elegidos = []
    for b in libres:
        if len(elegidos) == descartar:
            break
        if elegidos and b == elegidos[-1] + 1:
            continue   # adyacente al anterior: los dos huecos se fusionarian
        elegidos.append(b)

    if len(elegidos) < descartar:
        raise SystemExit(
            f"No hay {descartar} bloques descartables no adyacentes en '{secciones}'"
        )

    n = len(secciones) * pulsos
    k = n - len(elegidos) * pulsos
    return k, 0.0, elegidos


# ---------------------------------------------------------------------------
# Bordes
# ---------------------------------------------------------------------------

def optimo_borde(features, k):
    # Los tres bordes tienen una unica seleccion factible, asi que su costo es
    # el optimo:
    #   k = 2  -> [1, n], un solo salto
    #   k = n  -> se conservan todos los pulsos, no hay ningun salto: costo 0
    #   n = 2  -> cae en los dos casos anteriores a la vez
    n = len(features)
    if k == n:
        return 0.0
    if k == 2:
        return math.dist(features[1], features[n - 1])
    return None


# ---------------------------------------------------------------------------
# Instancias invalidas, para testear el parsing
# ---------------------------------------------------------------------------

INVALIDAS = {
    "cabecera_rota.txt": "esto no es una cabecera\n",
    "n_menor_que_2.txt": "1 1 2\n0.5\n",
    "d_cero.txt": "3 0 2\n\n\n\n",
    "k_mayor_que_n.txt": "4 1 9\n0.1\n0.2\n0.3\n0.4\n",
    "k_menor_que_2.txt": "4 1 1\n0.1\n0.2\n0.3\n0.4\n",
    "faltan_features.txt": "4 2 3\n0.1 0.2\n0.3 0.4\n0.5 0.6\n",
}


# ---------------------------------------------------------------------------
# La suite versionada
# ---------------------------------------------------------------------------

# (archivo, familia, parametros...). El costo optimo se conoce en las
# estructuradas y en los bordes; en las aleatorias lo determina el oraculo.
SUITE_ALEATORIAS = [
    # archivo,                    n,  d,  k, semilla
    ("ale_n08_d01_k04.txt",        8,  1,  4, 1),
    ("ale_n10_d03_k05.txt",       10,  3,  5, 2),
    ("ale_n12_d12_k06.txt",       12, 12,  6, 3),
    ("ale_n12_d01_k03.txt",       12,  1,  3, 4),
    ("ale_n14_d02_k07.txt",       14,  2,  7, 5),
    ("ale_n16_d12_k08.txt",       16, 12,  8, 6),
]

SUITE_ESTRUCTURADAS = [
    # archivo,                        secciones, pulsos, d, descartar, semilla
    ("est_ABBCBB_m2_desc1.txt",       "ABBCBB",  2,      4,  1,        11),
    ("est_ABBCBB_m2_desc2.txt",       "ABBCBB",  2,      4,  2,        12),
    ("est_ABBCBB_m3_desc1.txt",       "ABBCBB",  3,     12,  1,        13),
    ("est_ABBA_m2_desc1.txt",         "ABBA",    2,      3,  1,        14),
]

SUITE_BORDES = [
    # archivo,               n,  d,  k, semilla
    ("borde_n02_d01.txt",     2,  1,  2, 21),
    ("borde_k2_n10_d03.txt", 10,  3,  2, 22),
    ("borde_kn_n08_d02.txt",  8,  2,  8, 23),
]


def generar_suite(directorio):
    filas = []

    for archivo, n, d, k, semilla in SUITE_ALEATORIAS:
        features = aleatoria(n, d, semilla)
        escribir(os.path.join(directorio, archivo), features, k)
        filas.append({
            "archivo": archivo, "familia": "aleatoria",
            "n": n, "d": d, "k": k, "semilla": semilla,
            "costo_optimo": "",
            "descripcion": f"uniforme en [0,1)^{d}, independiente por pulso",
        })

    for archivo, secciones, pulsos, d, descartar, semilla in SUITE_ESTRUCTURADAS:
        k, optimo, bloques = optimo_estructurada(secciones, pulsos, descartar)
        features = estructurada(secciones, pulsos, d, semilla)
        escribir(os.path.join(directorio, archivo), features, k)
        filas.append({
            "archivo": archivo, "familia": "estructurada",
            "n": len(features), "d": d, "k": k, "semilla": semilla,
            "costo_optimo": repr(optimo),
            "descripcion": f"{secciones} de {pulsos} pulsos; descarta los bloques {bloques}",
        })

    for archivo, n, d, k, semilla in SUITE_BORDES:
        features = aleatoria(n, d, semilla)
        escribir(os.path.join(directorio, archivo), features, k)
        optimo = optimo_borde(features, k)
        filas.append({
            "archivo": archivo, "familia": "borde",
            "n": n, "d": d, "k": k, "semilla": semilla,
            "costo_optimo": "" if optimo is None else repr(optimo),
            "descripcion": "unica seleccion factible",
        })

    invalidas = os.path.join(directorio, "invalidas")
    os.makedirs(invalidas, exist_ok=True)
    for archivo, contenido in sorted(INVALIDAS.items()):
        with open(os.path.join(invalidas, archivo), "w") as f:
            f.write(contenido)

    manifiesto = os.path.join(directorio, "manifiesto.csv")
    with open(manifiesto, "w", newline="") as f:
        campos = ["archivo", "familia", "n", "d", "k", "semilla", "costo_optimo", "descripcion"]
        escritor = csv.DictWriter(f, fieldnames=campos)
        escritor.writeheader()
        for fila in filas:
            escritor.writerow(fila)

    print(f"Escritas {len(filas)} instancias validas y {len(INVALIDAS)} invalidas en {directorio}")
    print(f"Manifiesto: {manifiesto}")


def leer_manifiesto(directorio):
    with open(os.path.join(directorio, "manifiesto.csv"), newline="") as f:
        return list(csv.DictReader(f))


def main():
    parser = argparse.ArgumentParser(description="Genera instancias del problema.")
    sub = parser.add_subparsers(dest="comando", required=True)

    p_ale = sub.add_parser("aleatoria", help="features uniformes en [0,1)^d")
    p_ale.add_argument("--n", type=int, required=True)
    p_ale.add_argument("--d", type=int, required=True)
    p_ale.add_argument("--k", type=int, required=True)
    p_ale.add_argument("--semilla", type=int, default=0)
    p_ale.add_argument("--salida", required=True)

    p_est = sub.add_parser("estructurada", help="secciones repetidas, con optimo conocido")
    p_est.add_argument("--secciones", default="ABBCBB", help="una letra por bloque")
    p_est.add_argument("--pulsos", type=int, default=2, help="pulsos por bloque")
    p_est.add_argument("--d", type=int, default=12)
    p_est.add_argument("--descartar", type=int, default=1, help="bloques a descartar; fija k")
    p_est.add_argument("--ruido", type=float, default=0.0,
                       help="desvio del ruido gaussiano; con ruido > 0 el optimo deja de ser 0")
    p_est.add_argument("--semilla", type=int, default=0)
    p_est.add_argument("--salida", required=True)

    p_suite = sub.add_parser("suite", help="regenera todas las instancias versionadas")
    p_suite.add_argument("--directorio", default=None)

    args = parser.parse_args()

    if args.comando == "aleatoria":
        if not 2 <= args.k <= args.n:
            raise SystemExit("Debe cumplirse 2 <= k <= n.")
        escribir(args.salida, aleatoria(args.n, args.d, args.semilla), args.k)
        print(f"Escrita {args.salida}: n={args.n}, d={args.d}, k={args.k}")

    elif args.comando == "estructurada":
        k, optimo, bloques = optimo_estructurada(args.secciones, args.pulsos, args.descartar)
        features = estructurada(args.secciones, args.pulsos, args.d, args.semilla, args.ruido)
        escribir(args.salida, features, k)
        print(f"Escrita {args.salida}: n={len(features)}, d={args.d}, k={k}")
        print(f"Bloques descartados: {bloques}")
        if args.ruido > 0.0:
            print("Con ruido > 0 el optimo ya no es 0 y hay que calcularlo con el oraculo.")
        else:
            print(f"Costo optimo conocido: {optimo}")

    elif args.comando == "suite":
        directorio = args.directorio
        if directorio is None:
            aca = os.path.dirname(os.path.abspath(__file__))
            directorio = os.path.join(os.path.dirname(aca), "input", "instancias")
        generar_suite(directorio)


if __name__ == "__main__":
    main()
