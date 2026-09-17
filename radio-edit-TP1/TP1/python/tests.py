#!/usr/bin/env python3

import argparse
import math
import os
import subprocess
import sys
import tempfile

import generador
import oraculo

# Suite de tests del TP.
#
# Corre el ejecutable de C++ sobre las instancias versionadas de
# TP1/input/instancias/ y chequea siete cosas distintas:
#
#   1. HUMO             el ejemplo del enunciado da 1 2 4 6 con costo 2.0
#   2. SALIDA VALIDA    la seleccion tiene k pulsos, empieza en 1, termina en n
#                       y es estrictamente creciente
#   3. COINCIDENCIA     FB, BT y PD dan el mismo costo optimo
#   4. COSTO REPORTADO  el costo que imprime el C++ coincide con el costo de la
#                       seleccion que devuelve, recalculado en Python
#   5. ORACULO          ese costo coincide con el de una fuerza bruta
#                       independiente (oraculo.py)
#   6. OPTIMO CONOCIDO  en las estructuradas y en los bordes, coincide ademas
#                       con el optimo derivado analiticamente
#   7. ERRORES          las instancias mal formadas terminan con codigo != 0
#
# Los chequeos 4 y 5 son distintos y los dos hacen falta: el 4 detecta que el
# costo acumulado se desincronice de la seleccion devuelta (el riesgo tipico de
# BT, que lleva el costo incremental) y el 5 detecta que la seleccion no sea la
# optima.
#
# Uso:  python3 tests.py [--rapido] [--verboso]
#
# Solo usa la biblioteca estandar.

AQUI = os.path.dirname(os.path.abspath(__file__))
TP1 = os.path.dirname(AQUI)
BINARIO = os.path.join(TP1, "radioedit")   # lo puede reemplazar --binario
INSTANCIAS = os.path.join(TP1, "input", "instancias")
EJEMPLO = os.path.join(TP1, "input", "ejemplo.txt")

ALGORITMOS = ["fb", "bt", "pd"]

# Tolerancia: el C++ imprime con setprecision(10), asi que comparar por igualdad
# exacta de doubles no tiene sentido (ver la convencion en CLAUDE.md).
REL = 1e-6
ABS = 1e-9

# Arriba de esto el oraculo tarda demasiado: C(n-2, k-2) selecciones.
LIMITE_ORACULO = 500_000


def iguales(a, b):
    return math.isclose(a, b, rel_tol=REL, abs_tol=ABS)


class Resultados:
    def __init__(self, verboso):
        self.verboso = verboso
        self.ok = 0
        self.fallas = []
        self.grupo = ""

    def abrir(self, grupo):
        self.grupo = grupo
        print(f"\n{grupo}")

    def chequear(self, condicion, descripcion, detalle=""):
        if condicion:
            self.ok += 1
            if self.verboso:
                print(f"  ok    {descripcion}")
        else:
            self.fallas.append((self.grupo, descripcion, detalle))
            print(f"  FALLA {descripcion}")
            if detalle:
                print(f"        {detalle}")

    def cerrar(self, cuantos):
        print(f"  ({cuantos} chequeos)")


def correr(instancia, algoritmo, directorio):
    salida = os.path.join(directorio, f"seleccion_{algoritmo}.txt")
    proceso = subprocess.run(
        [BINARIO, "--instancia", instancia, "--algoritmo", algoritmo, "--salida", salida],
        capture_output=True, text=True,
    )
    return proceso, salida


def leer_seleccion(ruta):
    # El archivo tiene una unica linea con los k enteros 1-based.
    with open(ruta) as f:
        return [int(x) for x in f.read().split()]


def costo_impreso(stdout):
    for linea in stdout.splitlines():
        if linea.startswith("Costo:"):
            return float(linea.split(":", 1)[1])
    return None


def seleccion_impresa(stdout):
    for linea in stdout.splitlines():
        if linea.startswith("Seleccion:"):
            return [int(x) for x in linea.split(":", 1)[1].split()]
    return None


def resolver_con(instancia, algoritmo, directorio):
    # Devuelve (seleccion 1-based, costo impreso, stdout), o None si el binario
    # fallo. Un crash tiene que quedar registrado como una falla mas, no abortar
    # la corrida: si no, una instancia rota esconde el resultado de las demas.
    proceso, salida = correr(instancia, algoritmo, directorio)
    if proceso.returncode != 0:
        return None
    return leer_seleccion(salida), costo_impreso(proceso.stdout), proceso.stdout


# ---------------------------------------------------------------------------
# 1. Humo
# ---------------------------------------------------------------------------

def test_humo(res, directorio, algoritmos):
    res.abrir("[1] humo: el ejemplo del enunciado")
    hechos = 0
    for algoritmo in algoritmos:
        salida = resolver_con(EJEMPLO, algoritmo, directorio)
        if salida is None:
            res.chequear(False, f"{algoritmo}: termina sin error", "el binario fallo")
            hechos += 1
            continue
        seleccion, costo, _ = salida
        res.chequear(seleccion == [1, 2, 4, 6],
                     f"{algoritmo}: seleccion 1 2 4 6",
                     f"devolvio {seleccion}")
        res.chequear(iguales(costo, 2.0),
                     f"{algoritmo}: costo 2.0",
                     f"devolvio {costo}")
        hechos += 2
    res.cerrar(hechos)


# ---------------------------------------------------------------------------
# 2-6. Chequeos sobre cada instancia valida
# ---------------------------------------------------------------------------

def test_instancias(res, directorio, algoritmos, manifiesto):
    res.abrir("[2] salida valida: k pulsos, de 1 a n, estrictamente creciente")
    hechos = 0
    costos = {}

    for fila in manifiesto:
        ruta = os.path.join(INSTANCIAS, fila["archivo"])
        n, k = int(fila["n"]), int(fila["k"])
        costos[fila["archivo"]] = {}

        for algoritmo in algoritmos:
            etiqueta = f"{fila['archivo']} / {algoritmo}"
            salida = resolver_con(ruta, algoritmo, directorio)
            if salida is None:
                res.chequear(False, f"{etiqueta}: termina sin error", "el binario fallo")
                costos[fila["archivo"]][algoritmo] = None
                hechos += 1
                continue
            seleccion, costo, stdout = salida
            costos[fila["archivo"]][algoritmo] = (seleccion, costo)

            valida = (len(seleccion) == k
                      and seleccion[0] == 1
                      and seleccion[-1] == n
                      and all(a < b for a, b in zip(seleccion, seleccion[1:])))
            res.chequear(valida, f"{etiqueta}: seleccion factible",
                         f"n={n}, k={k}, devolvio {seleccion}")

            res.chequear(seleccion_impresa(stdout) == seleccion,
                         f"{etiqueta}: lo impreso coincide con lo guardado")
            hechos += 2
    res.cerrar(hechos)

    res.abrir("[3] coincidencia: FB, BT y PD dan el mismo costo optimo")
    hechos = 0
    for fila in manifiesto:
        por_algoritmo = costos[fila["archivo"]]
        if por_algoritmo[algoritmos[0]] is None:
            continue
        referencia = por_algoritmo[algoritmos[0]][1]
        for algoritmo in algoritmos[1:]:
            if por_algoritmo[algoritmo] is None:
                continue
            res.chequear(iguales(referencia, por_algoritmo[algoritmo][1]),
                         f"{fila['archivo']}: {algoritmos[0]} == {algoritmo}",
                         f"{referencia} vs {por_algoritmo[algoritmo][1]}")
            hechos += 1
    res.cerrar(hechos)

    res.abrir("[4] costo reportado: coincide con el costo de la seleccion devuelta")
    hechos = 0
    for fila in manifiesto:
        ruta = os.path.join(INSTANCIAS, fila["archivo"])
        _, _, _, features = oraculo.leer_instancia(ruta)
        for algoritmo in algoritmos:
            if costos[fila["archivo"]][algoritmo] is None:
                continue
            seleccion, costo = costos[fila["archivo"]][algoritmo]
            recalculado = oraculo.costo_seleccion(features, [p - 1 for p in seleccion])
            res.chequear(iguales(costo, recalculado),
                         f"{fila['archivo']} / {algoritmo}: costo verificable",
                         f"el C++ dijo {costo}, la seleccion cuesta {recalculado}")
            hechos += 1
    res.cerrar(hechos)

    res.abrir("[5] oraculo: coincide con la fuerza bruta independiente en Python")
    hechos = 0
    for fila in manifiesto:
        ruta = os.path.join(INSTANCIAS, fila["archivo"])
        n, _, k, features = oraculo.leer_instancia(ruta)

        cuantas = oraculo.combinaciones(n, k)
        if cuantas > LIMITE_ORACULO:
            print(f"  --    {fila['archivo']}: salteada ({cuantas} selecciones)")
            continue

        optimo, _ = oraculo.resolver(n, k, features)
        for algoritmo in algoritmos:
            if costos[fila["archivo"]][algoritmo] is None:
                continue
            _, costo = costos[fila["archivo"]][algoritmo]
            res.chequear(iguales(costo, optimo),
                         f"{fila['archivo']} / {algoritmo}: es el optimo",
                         f"el C++ dijo {costo}, el oraculo {optimo}")
            hechos += 1
    res.cerrar(hechos)

    res.abrir("[6] optimo conocido: coincide con el derivado analiticamente")
    hechos = 0
    for fila in manifiesto:
        if not fila["costo_optimo"]:
            continue
        esperado = float(fila["costo_optimo"])
        for algoritmo in algoritmos:
            if costos[fila["archivo"]][algoritmo] is None:
                continue
            _, costo = costos[fila["archivo"]][algoritmo]
            res.chequear(iguales(costo, esperado),
                         f"{fila['archivo']} / {algoritmo}: costo {esperado:.10g}",
                         f"devolvio {costo}")
            hechos += 1
    res.cerrar(hechos)


# ---------------------------------------------------------------------------
# 7. Errores de parsing
# ---------------------------------------------------------------------------

def test_errores(res, directorio):
    res.abrir("[7] errores: las instancias mal formadas fallan con codigo != 0")
    hechos = 0

    invalidas = os.path.join(INSTANCIAS, "invalidas")
    casos = sorted(os.listdir(invalidas))
    casos = [os.path.join(invalidas, c) for c in casos if c.endswith(".txt")]
    casos.append(os.path.join(invalidas, "no_existe_este_archivo.txt"))

    for ruta in casos:
        proceso, _ = correr(ruta, "pd", directorio)
        nombre = os.path.basename(ruta)
        res.chequear(proceso.returncode != 0,
                     f"{nombre}: termina con error",
                     f"codigo {proceso.returncode}, stdout: {proceso.stdout.strip()[:120]}")
        res.chequear("Error:" in proceso.stderr,
                     f"{nombre}: explica el problema por stderr",
                     f"stderr: {proceso.stderr.strip()[:120]}")
        hechos += 2

    res.cerrar(hechos)


# ---------------------------------------------------------------------------

def preparar():
    if not os.path.exists(os.path.join(INSTANCIAS, "manifiesto.csv")):
        print("Instancias no encontradas: generandolas.")
        generador.generar_suite(INSTANCIAS)

    if not os.path.exists(BINARIO):
        print("Binario no encontrado: compilando con make.")
        compilacion = subprocess.run(["make", "-C", TP1], capture_output=True, text=True)
        if compilacion.returncode != 0:
            print(compilacion.stdout)
            print(compilacion.stderr)
            raise SystemExit("No se pudo compilar. Correr 'make' a mano en TP1/.")


def main():
    parser = argparse.ArgumentParser(description="Suite de tests del TP1.")
    parser.add_argument("--rapido", action="store_true",
                        help="saltea fuerza bruta, que es la que tarda")
    parser.add_argument("--verboso", action="store_true",
                        help="imprime tambien los chequeos que pasan")
    parser.add_argument("--binario", default=None,
                        help="ejecutable a testear; por defecto TP1/radioedit. "
                             "Sirve para correr la suite contra otra implementacion.")
    args = parser.parse_args()

    global BINARIO
    if args.binario:
        BINARIO = os.path.abspath(args.binario)
        if not os.path.exists(BINARIO):
            raise SystemExit(f"No existe el binario {BINARIO}")

    preparar()

    algoritmos = ["bt", "pd"] if args.rapido else ALGORITMOS
    manifiesto = generador.leer_manifiesto(INSTANCIAS)

    print("Suite de tests — TP1 recorte consciente de audio")
    print(f"binario     : {BINARIO}")
    print(f"instancias  : {INSTANCIAS} ({len(manifiesto)} validas)")
    print(f"algoritmos  : {', '.join(algoritmos)}")

    res = Resultados(args.verboso)

    with tempfile.TemporaryDirectory() as directorio:
        test_humo(res, directorio, algoritmos)
        test_instancias(res, directorio, algoritmos, manifiesto)
        test_errores(res, directorio)

    print("\n" + "-" * 70)
    if res.fallas:
        print(f"{len(res.fallas)} FALLAS de {res.ok + len(res.fallas)} chequeos\n")
        for grupo, descripcion, detalle in res.fallas:
            print(f"  {grupo}")
            print(f"    {descripcion}")
            if detalle:
                print(f"    {detalle}")
        return 1

    print(f"{res.ok} chequeos, todos OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
