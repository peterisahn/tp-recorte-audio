#!/usr/bin/env python3
"""Port a Python de source/main.cpp.

Mismo CLI, misma salida y mismos codigos de retorno que ./radioedit, para que
la suite de tests pueda correrse contra cualquiera de las dos implementaciones:

    python3 python/tests.py                        # contra el C++
    python3 python/tests.py --binario python/main.py   # contra este port

Que las dos pasen los mismos 223 chequeos es lo que permite comparar tiempos
sin dudar de si estan resolviendo el mismo problema.
"""

import os
import sys
import time

from backtracking import Backtracking
from fuerza_bruta import FuerzaBruta
from instancia import Instancia
from programacion_dinamica import ProgramacionDinamica


def crear_algoritmo(algoritmo):
    if algoritmo == "fb":
        return FuerzaBruta()
    if algoritmo == "bt":
        return Backtracking()
    if algoritmo == "pd":
        return ProgramacionDinamica()
    raise RuntimeError("Algoritmo desconocido: " + algoritmo + ". Usar fb, bt o pd.")


def ajustar_recursion(instancia):
    # DIFERENCIA CON C++, y es la segunda diferencia grande del port.
    #
    # Los tres algoritmos son recursivos. FB y BT bajan un nivel por pulso, asi
    # que llegan a profundidad ~n; PD baja un nivel por pulso conservado, asi
    # que llega a ~k. En C++ eso no es problema. Python en cambio corta a las
    # 1.000 llamadas por defecto y tira RecursionError, asi que con n o k en los
    # cientos el port fallaba solo, sin ser un bug del algoritmo.
    #
    # El limite se sube con margen: cuenta TODOS los frames, no solo los de la
    # recursion, y cada nivel de pd() apila ademas el frame de costo().
    sys.setrecursionlimit(max(3000, 10 * (instancia.n() + instancia.k())))


def registrar_csv(ruta, algoritmo, instancia, costo, ms):
    existe = os.path.exists(ruta)

    try:
        with open(ruta, "a") as csv:
            if not existe:
                csv.write("algoritmo,n,d,k,costo,ms\n")
            csv.write("{},{},{},{},{},{}\n".format(
                algoritmo, instancia.n(), instancia.d(), instancia.k(),
                format(costo, ".10g"), format(ms, ".10g")))
    except OSError:
        return


def resolver_instancia(ruta_entrada, algoritmo, ruta_csv, ruta_salida_pedida):
    instancia = Instancia(ruta_entrada)
    print("Instancia cargada: n={} pulsos, d={} características, k={} a conservar".format(
        instancia.n(), instancia.d(), instancia.k()))

    solver = crear_algoritmo(algoritmo)
    ajustar_recursion(instancia)

    inicio = time.perf_counter()
    solucion = solver.resolver(instancia)
    fin = time.perf_counter()

    ms = (fin - inicio) * 1000.0

    if not solucion.esValida(instancia):
        print("Atención: la selección devuelta no es válida. Debe tener exactamente "
              "{} pulsos, empezar en 1, terminar en {} y ser estrictamente creciente.".format(
                  instancia.k(), instancia.n()))

    solucion.imprimir(instancia)
    print("Tiempo: {} ms".format(format(ms, ".10g")))

    ruta_salida = ruta_salida_pedida
    if not ruta_salida:
        ruta_salida = "output/numericos/seleccion_" + algoritmo + ".txt"
    solucion.guardar(ruta_salida)
    print("Resultado guardado en " + ruta_salida)

    if ruta_csv:
        registrar_csv(ruta_csv, algoritmo, instancia, solucion.costo(instancia), ms)
        print("Medición agregada a " + ruta_csv)


def imprimir_uso():
    print("Uso:\n"
          "  ./main.py --instancia <archivo> --algoritmo <fb|bt|pd>\n"
          "             [--salida <archivo>] [--csv <archivo>]\n"
          "\nEjemplos:\n"
          "  ./main.py --instancia input/ejemplo.txt --algoritmo pd\n"
          "  ./main.py --instancia input/ejemplo.txt --algoritmo bt --csv output/numericos/tiempos.csv")


def main(argv):
    if len(argv) < 2:
        imprimir_uso()
        return 1

    ruta_archivo = ""
    algoritmo = "pd"
    ruta_csv = ""
    ruta_salida = ""

    i = 1
    while i < len(argv):
        arg = argv[i]
        if arg == "--instancia" and i + 1 < len(argv):
            i += 1
            ruta_archivo = argv[i]
        elif arg == "--algoritmo" and i + 1 < len(argv):
            i += 1
            algoritmo = argv[i]
        elif arg == "--salida" and i + 1 < len(argv):
            i += 1
            ruta_salida = argv[i]
        elif arg == "--csv" and i + 1 < len(argv):
            i += 1
            ruta_csv = argv[i]
        elif arg in ("--ayuda", "--help"):
            imprimir_uso()
            return 0
        i += 1

    if not ruta_archivo:
        imprimir_uso()
        return 1

    try:
        resolver_instancia(ruta_archivo, algoritmo, ruta_csv, ruta_salida)
    except Exception as e:
        print("Error: {}".format(e), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
