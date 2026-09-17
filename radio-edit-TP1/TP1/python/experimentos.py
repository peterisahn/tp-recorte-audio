#!/usr/bin/env python3
"""experimentos.py - driver de la experimentacion del TP1.

Corre los experimentos del punto 3 y deja los resultados CRUDOS en
experimentos/resultados/. Una fila por corrida: nada se promedia aca, para que
el analisis se pueda rehacer sin volver a medir.

    python3 python/experimentos.py --todos     # los 4 del informe, desde cero
    python3 python/experimentos.py exp1        # uno solo del informe, desde cero
    python3 python/experimentos.py e1          # un experimento por su nombre interno
    python3 python/experimentos.py --lista     # ver cuales hay
    python3 python/experimentos.py --completo  # los 12 del script

Es REANUDABLE: si lo cortas a la mitad, la proxima vez saltea las celdas que ya
tienen sus corridas completas. Asi un barrido largo se puede hacer de a ratos.

Solo usa la biblioteca estandar (ver requirements.txt de la catedra).
"""

import argparse
import csv
import math
import os
import platform
import re
import statistics
import subprocess
import sys
import time

import generador

# ---------------------------------------------------------------------------
# Configuracion
# ---------------------------------------------------------------------------

ACA = os.path.dirname(os.path.abspath(__file__))
TP1 = os.path.dirname(ACA)
RAIZ = os.path.dirname(TP1)
RESULTADOS = os.path.join(RAIZ, "experimentos", "resultados")
TRABAJO = os.path.join(TP1, "output", "experimentos")

BINARIO_CPP = os.path.join(TP1, "radioedit")
BINARIO_PY = os.path.join(ACA, "main.py")

# Instancias distintas por celda: los tiempos (y sobre todo los nodos de BT)
# dependen de la instancia, no solo de n y k. Una sola instancia no alcanza.
SEMILLAS = 3
# Corridas por instancia. El instructivo de la catedra pide 10 para promediar.
REPETICIONES = 10
# E3 usa mas instancias por celda: ahi cambiamos d, y cambiar d regenera TODAS
# las features, asi que dos celdas vecinas no comparten instancia. Con 3
# semillas la mediana de nodos de BT se mueve por el sorteo y no por d.
E3_SEMILLAS = 5
# Si una sola corrida tarda mas que esto, damos el algoritmo por no viable a
# ese tamano y dejamos de probarlo mas arriba. El punto de quiebre queda siendo
# un resultado medido y no una decision nuestra.
LIMITE_SEGUNDOS = 10.0

COLUMNAS = ["experimento", "algoritmo", "implementacion", "familia",
            "n", "d", "k", "semilla", "repeticion", "ms", "costo", "nodos",
            "poda_fact", "poda_opt"]

# Binario con contadores, para los experimentos que miden nodos explorados.
# Se arma con `make instrumentado` y sale de los mismos fuentes que radioedit.
BINARIO_INSTR = os.path.join(TP1, "radioedit_instr")


# ---------------------------------------------------------------------------
# Entorno: el instructivo (pag. 14) exige declararlo en el informe
# ---------------------------------------------------------------------------

def entorno():
    def cmd(args):
        try:
            return subprocess.run(args, capture_output=True, text=True).stdout.strip().splitlines()[0]
        except Exception:
            return "desconocido"

    return {
        "sistema": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "procesador": cmd(["sysctl", "-n", "machdep.cpu.brand_string"]),
        "memoria_gb": round(int(cmd(["sysctl", "-n", "hw.memsize"]) or 0) / 1024**3) or "desconocido",
        "compilador": cmd(["g++", "--version"]),
        "python": sys.version.split()[0],
        "flags_cpp": "-std=c++17 -O2 -Wall -Wextra",
        "semillas_por_celda": f"{SEMILLAS} (E3 usa {E3_SEMILLAS})",
        "repeticiones_por_instancia": REPETICIONES,
        "fecha": time.strftime("%Y-%m-%d %H:%M"),
    }


def guardar_entorno():
    ruta = os.path.join(os.path.dirname(RESULTADOS), "entorno.txt")
    if RESULTADOS != os.path.join(RAIZ, "experimentos", "resultados"):
        os.makedirs(RESULTADOS, exist_ok=True)
        ruta = os.path.join(RESULTADOS, "entorno.txt")
    with open(ruta, "w") as f:
        f.write("Entorno de ejecucion de la experimentacion\n")
        f.write("=" * 50 + "\n\n")
        for clave, valor in entorno().items():
            f.write(f"{clave:28} {valor}\n")
    return ruta


# ---------------------------------------------------------------------------
# Correr una instancia
# ---------------------------------------------------------------------------

# Patron de secciones de las instancias estructuradas. Imita la Figura 1 del
# enunciado: estrofa - estribillo - estribillo - puente - estribillo - estribillo.
# Tiene 6 secciones, asi que los n estructurados son multiplos de 6.
PATRON = "ABBCBB"


def instancia(familia, n, d, k, semilla):
    """Genera la instancia y devuelve su ruta. Determinista: misma semilla,
    mismos bytes, asi que el experimento es reproducible.

    Tres familias:
      aleatoria            cada caracteristica sorteada aparte. Ninguna repeticion,
                           asi que casi ningun salto sale barato: es el caso adverso.
      estructurada         secciones ABBCBB que se repiten IDENTICAS. Es el caso de
                           uso real llevado al extremo: hay cortes que cuestan 0.
      estructurada_r<x>    lo mismo pero con ruido gaussiano de desvio 0,0<x> encima.
                           Un estribillo real no suena identico dos veces; el ruido
                           es el que dice cuanta imperfeccion tolera cada algoritmo."""
    os.makedirs(TRABAJO, exist_ok=True)
    ruta = os.path.join(TRABAJO, f"{familia}_n{n}_d{d}_k{k}_s{semilla}.txt")
    if familia == "aleatoria":
        features = generador.aleatoria(n, d, semilla)
    elif familia.startswith("estructurada"):
        if n % len(PATRON) != 0:
            raise SystemExit(f"n={n} no es multiplo de {len(PATRON)} (patron {PATRON})")
        ruido = 0.0
        if "_r" in familia:
            ruido = float(familia.split("_r")[1])
        features = generador.estructurada(PATRON, n // len(PATRON), d, semilla, ruido)
    else:
        raise SystemExit(f"Familia desconocida: {familia}")
    generador.escribir(ruta, features, k)
    return ruta


def correr(binario, algoritmo, ruta_instancia, tope=None):
    """Corre el binario una vez. Devuelve un dict con la medicion, o None.

    El tiempo lo reporta el propio binario y mide SOLO resolver(): no incluye
    leer el archivo ni escribir la salida, que son iguales para los tres
    algoritmos y ensuciarian la comparacion.

    Los campos de nodos y podas solo aparecen si el binario es el instrumentado.

    `tope` corta la corrida a los N segundos y devuelve None. Hace falta: en las
    instancias de audio real fuerza bruta no termina NUNCA, y sin tope la sonda
    que deberia declararla no viable se queda colgada esperandola."""
    try:
        proceso = subprocess.run(
            [binario, "--instancia", ruta_instancia, "--algoritmo", algoritmo,
             "--salida", os.path.join(TRABAJO, "salida.txt")],
            capture_output=True, text=True, cwd=TP1,
            timeout=tope if tope else None)
    except subprocess.TimeoutExpired:
        return None
    if proceso.returncode != 0:
        return None
    ms = re.search(r"Tiempo: ([\d.eE+-]+)", proceso.stdout)
    costo = re.search(r"Costo: ([\d.eE+-]+)", proceso.stdout)
    if not ms or not costo:
        return None
    nodos = re.search(r"Nodos: (\d+)", proceso.stdout)
    podas = re.search(r"PodaFactibilidad: (\d+) PodaOptimalidad: (\d+)", proceso.stdout)
    return {
        "ms": float(ms.group(1)),
        "costo": float(costo.group(1)),
        "nodos": int(nodos.group(1)) if nodos else "",
        "poda_fact": int(podas.group(1)) if podas else "",
        "poda_opt": int(podas.group(2)) if podas else "",
    }


# ---------------------------------------------------------------------------
# Escritura y reanudacion
# ---------------------------------------------------------------------------

def ruta_csv(experimento):
    os.makedirs(RESULTADOS, exist_ok=True)
    return os.path.join(RESULTADOS, f"{experimento}.csv")


def leer_hechas(experimento, repeticiones=None):
    """Devuelve el conjunto de celdas que ya tienen todas sus corridas."""
    repeticiones = REPETICIONES if repeticiones is None else repeticiones
    ruta = ruta_csv(experimento)
    if not os.path.exists(ruta):
        return set()
    cuenta = {}
    with open(ruta, newline="") as f:
        for fila in csv.DictReader(f):
            clave = (fila["algoritmo"], fila["implementacion"], fila["familia"],
                     fila["n"], fila["d"], fila["k"], fila["semilla"])
            cuenta[clave] = cuenta.get(clave, 0) + 1
    return {c for c, v in cuenta.items() if v >= repeticiones}


def abrir_csv(experimento):
    ruta = ruta_csv(experimento)
    existe = os.path.exists(ruta)
    f = open(ruta, "a", newline="")
    escritor = csv.DictWriter(f, fieldnames=COLUMNAS)
    if not existe:
        escritor.writeheader()
    return f, escritor


def medir_celda(escritor, experimento, algoritmo, impl, binario,
                familia, n, d, k, semilla, hechas, repeticiones=None):
    """Mide una celda completa. Devuelve la mediana en ms, o None si no es viable."""
    repeticiones = REPETICIONES if repeticiones is None else repeticiones
    clave = (algoritmo, impl, familia, str(n), str(d), str(k), str(semilla))
    if clave in hechas:
        return "ya"

    ruta = instancia(familia, n, d, k, semilla)

    # Sonda: una corrida para ver si vale la pena hacer las 10.
    arranque = time.perf_counter()
    sonda = correr(binario, algoritmo, ruta, tope=LIMITE_SEGUNDOS * 1.5)
    transcurrido = time.perf_counter() - arranque
    if sonda is None:
        return None
    if transcurrido > LIMITE_SEGUNDOS:
        return -1.0   # marca de "no viable"

    def fila(res, r):
        f = dict(experimento=experimento, algoritmo=algoritmo, implementacion=impl,
                 familia=familia, n=n, d=d, k=k, semilla=semilla, repeticion=r)
        f.update(res)
        return f

    tiempos = [sonda["ms"]]
    filas = [fila(sonda, 1)]
    for r in range(2, repeticiones + 1):
        res = correr(binario, algoritmo, ruta)
        if res is None:
            return None
        tiempos.append(res["ms"])
        filas.append(fila(res, r))
    for fila in filas:
        escritor.writerow(fila)
    return statistics.median(tiempos)


# ---------------------------------------------------------------------------
# E1 - Escalabilidad en n
# ---------------------------------------------------------------------------

E1_TAMANOS = [10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 34, 40, 50, 60, 80,
              100, 150, 200, 300, 400, 600, 800, 1200, 1600, 2000]

def e1(args):
    """E1 - Escalabilidad en n.

    HIPOTESIS. FB y BT crecen de forma exponencial: cada par de pulsos extra
    multiplica el tiempo por un factor mas o menos constante, asi que dejan de
    correr muy temprano. PD crece como un polinomio (n^2*k, que con k=n/2 es
    cubico), asi que llega a los miles de pulsos que pide el enunciado. Debe
    existir un n a partir del cual PD gana por varios ordenes de magnitud.

    SE VARIA        n (cantidad de pulsos)
    SE CONTROLA     d=12, k=n/2, instancias aleatorias, semillas 0..2
    SE MIDE         tiempo de resolver(), en ms
    """
    experimento = "e1_escalabilidad_n"
    hechas = leer_hechas(experimento)
    f, escritor = abrir_csv(experimento)
    vivos = {"fb": True, "bt": True, "pd": True}
    quiebre = {}

    print(f"E1 - escalabilidad en n   (d=12, k=n/2, {SEMILLAS} instancias x {REPETICIONES} corridas)")
    print(f"{'n':>6} {'k':>6} | {'FB':>14} {'BT':>14} {'PD':>14}")
    print("-" * 62)

    try:
        for n in E1_TAMANOS:
            k = max(2, n // 2)
            if not any(vivos.values()):
                break
            celda = {}
            for alg in ("fb", "bt", "pd"):
                if not vivos[alg]:
                    celda[alg] = "--"
                    continue
                medianas = []
                for semilla in range(SEMILLAS):
                    m = medir_celda(escritor, experimento, alg, "cpp", BINARIO_CPP,
                                    "aleatoria", n, 12, k, semilla, hechas)
                    if m == -1.0:
                        vivos[alg] = False
                        quiebre[alg] = n
                        break
                    if m == "ya":
                        continue
                    if m is None:
                        vivos[alg] = False
                        break
                    medianas.append(m)
                f.flush()
                if not vivos[alg]:
                    celda[alg] = f">{LIMITE_SEGUNDOS:.0f}s"
                elif medianas:
                    celda[alg] = f"{statistics.median(medianas):,.3f} ms"
                else:
                    celda[alg] = "(ya estaba)"
            print(f"{n:>6} {k:>6} | {celda['fb']:>14} {celda['bt']:>14} {celda['pd']:>14}")
    finally:
        f.close()

    print()
    for alg in ("fb", "bt", "pd"):
        if alg in quiebre:
            print(f"  {alg.upper()} dejo de ser viable en n = {quiebre[alg]}")
        elif vivos[alg]:
            print(f"  {alg.upper()} llego hasta n = {E1_TAMANOS[-1]} sin romperse")
    print(f"\nResultados crudos en {os.path.relpath(RESULTADOS, RAIZ)}/{experimento}.csv")


# ---------------------------------------------------------------------------
# E2 - Cuanto se recorta (barrido de k)
# ---------------------------------------------------------------------------

E2_N = 24                       # el mayor n donde FB todavia corre para TODO k
E2_KS = [2, 3, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 23, 24]

def e2(args):
    """E2 - Cuanto influye cuanto se recorta.

    HIPOTESIS. La cantidad de recortes posibles es C(n-2, k-2): vale 1 cuando se
    conserva el minimo (k=2) y tambien 1 cuando se conserva todo (k=n), y es
    maxima cuando se conserva la mitad. Asi que FB deberia dibujar un arco:
    facil en los dos extremos, dificilisimo en el medio. BT deberia seguir la
    misma forma, y la pregunta es si las podas le rinden mas en alguna zona.
    PD en cambio no cuenta recortes sino que llena una tabla de n x k celdas, asi
    que su trabajo deberia crecer DERECHO con k, sin arco.

    SE VARIA        k (cuantos pulsos se conservan)
    SE CONTROLA     n=24, d=12, instancias aleatorias, semillas 0..2
    SE MIDE         tiempo de resolver() y nodos explorados por FB y BT
    """
    experimento = "e2_barrido_k"
    hechas = leer_hechas(experimento)
    f, escritor = abrir_csv(experimento)

    usar_instr = os.path.exists(BINARIO_INSTR)
    if not usar_instr:
        print("Aviso: no existe radioedit_instr, no se cuentan nodos.")
        print("       Corre 'make instrumentado' desde TP1/ y volve a intentar.\n")

    print(f"E2 - barrido de k   (n={E2_N}, d=12, {SEMILLAS} instancias x {REPETICIONES} corridas)")
    print(f"{'k':>4} {'recortes posibles':>18} | {'FB':>12} {'BT':>10} {'PD':>10} | "
          f"{'nodos FB':>10} {'nodos BT':>9} {'explora BT':>11}")
    print("-" * 96)

    try:
        for k in E2_KS:
            celda, nodos = {}, {}
            for alg in ("fb", "bt", "pd"):
                # Para FB y BT usamos el binario instrumentado: los contadores
                # estan detras de #ifdef y no cambian lo que se mide.
                binario = BINARIO_INSTR if (usar_instr and alg in ("fb", "bt")) else BINARIO_CPP
                medianas, nods = [], []
                for semilla in range(SEMILLAS):
                    m = medir_celda(escritor, experimento, alg, "cpp", binario,
                                    "aleatoria", E2_N, 12, k, semilla, hechas)
                    if m in (None, -1.0):
                        break
                    if m != "ya":
                        medianas.append(m)
                    r = correr(binario, alg, instancia("aleatoria", E2_N, 12, k, semilla))
                    if r and r["nodos"] != "":
                        nods.append(r["nodos"])
                f.flush()
                celda[alg] = f"{statistics.median(medianas):,.3f} ms" if medianas else "(ya)"
                nodos[alg] = int(statistics.median(nods)) if nods else 0
            pct = (100.0 * nodos["bt"] / nodos["fb"]) if nodos.get("fb") else 0
            print(f"{k:>4} {math.comb(E2_N-2, k-2):>18,} | {celda['fb']:>12} {celda['bt']:>10} "
                  f"{celda['pd']:>10} | {nodos['fb']:>10,} {nodos['bt']:>9,} {pct:>10.2f}%")
    finally:
        f.close()

    print(f"\nResultados crudos en {os.path.relpath(RESULTADOS, RAIZ)}/{experimento}.csv")



# ---------------------------------------------------------------------------
# E3 - Cuanto pesa la cantidad de caracteristicas (barrido de d)
# ---------------------------------------------------------------------------

E3_DS = [1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96]
# FB y BT se miden en una instancia chica, la mayor donde FB corre 12 veces
# seguidas sin que el barrido tarde horas.
E3_N_CHICO, E3_K_CHICO = 20, 10
# PD se mide en una instancia grande: en n=20 tarda 0,005 ms, que esta por
# debajo de la resolucion util del reloj y cualquier efecto de d se perderia en
# el ruido. n=600 la deja en decenas de ms, donde el efecto SI se ve.
E3_N_GRANDE, E3_K_GRANDE = 600, 300


def e3(args):
    """E3 - Cuanto pesa la cantidad de caracteristicas por pulso.

    HIPOTESIS. Las tres complejidades llevan un factor d, porque la distancia
    ||f_{i+1} - f_j|| recorre las d coordenadas. Cambiar d NO cambia cuantos
    recortes hay que revisar: la combinatoria depende solo de n y k. Asi que
    esperamos que el tiempo crezca de forma PROPORCIONAL a d (al doble de
    caracteristicas, el doble de tiempo) y que la cantidad de nodos de FB quede
    exactamente igual. Para BT no esta claro: sus podas miran los numeros, no
    solo la estructura, asi que d podria cambiarle la cantidad de nodos.

    SE VARIA        d (caracteristicas por pulso), de 1 a 64
    SE CONTROLA     n=20 k=10 para FB y BT; n=600 k=300 para PD; semillas 0..4
    SE MIDE         tiempo de resolver() y nodos explorados por FB y BT
    """
    experimento = "e3_barrido_d"
    hechas = leer_hechas(experimento)
    f, escritor = abrir_csv(experimento)

    usar_instr = os.path.exists(BINARIO_INSTR)
    if not usar_instr:
        print("Aviso: no existe radioedit_instr, no se cuentan nodos.")
        print("       Corre 'make instrumentado' desde TP1/ y volve a intentar.\n")

    # Cada algoritmo con su tamano. FB y BT comparten instancia; PD no puede,
    # y eso se aclara siempre que se reporte el numero.
    planes = [("fb", E3_N_CHICO,  E3_K_CHICO),
              ("bt", E3_N_CHICO,  E3_K_CHICO),
              ("pd", E3_N_GRANDE, E3_K_GRANDE)]

    print(f"E3 - barrido de d   (FB/BT en n={E3_N_CHICO} k={E3_K_CHICO}, "
          f"PD en n={E3_N_GRANDE} k={E3_K_GRANDE}, "
          f"{E3_SEMILLAS} instancias x {REPETICIONES} corridas)")
    print(f"{'d':>4} | {'FB':>12} {'BT':>10} {'PD':>12} | {'nodos FB':>10} {'nodos BT':>9}")
    print("-" * 70)

    base = {}
    try:
        for d in E3_DS:
            celda, nodos = {}, {}
            for alg, n, k in planes:
                binario = BINARIO_INSTR if (usar_instr and alg in ("fb", "bt")) else BINARIO_CPP
                medianas, nods = [], []
                for semilla in range(E3_SEMILLAS):
                    m = medir_celda(escritor, experimento, alg, "cpp", binario,
                                    "aleatoria", n, d, k, semilla, hechas)
                    if m in (None, -1.0):
                        break
                    if m != "ya":
                        medianas.append(m)
                    r = correr(binario, alg, instancia("aleatoria", n, d, k, semilla))
                    if r and r["nodos"] != "":
                        nods.append(r["nodos"])
                f.flush()
                celda[alg] = f"{statistics.median(medianas):,.3f} ms" if medianas else "(ya)"
                nodos[alg] = int(statistics.median(nods)) if nods else 0
                if medianas:
                    base.setdefault(alg, statistics.median(medianas))
            print(f"{d:>4} | {celda['fb']:>12} {celda['bt']:>10} {celda['pd']:>12} | "
                  f"{nodos['fb']:>10,} {nodos['bt']:>9,}")
    finally:
        f.close()

    print(f"\nResultados crudos en {os.path.relpath(RESULTADOS, RAIZ)}/{experimento}.csv")


# E3c - Control: de que depende el codo de PD
#
# En el barrido principal PD casi no se entera de d hasta d=16 y a partir de
# d=24 pasa a crecer proporcional. Ese codo hay que explicarlo, y la primera
# sospecha era la memoria: el arreglo de features ocupa n*d*8 bytes, asi que
# al crecer d en algun momento deja de entrar en la cache.
#
# Esa hipotesis es FALSABLE: si el codo fuera por el tamano del arreglo, al
# bajar n a la mitad el codo tendria que correrse al doble de d. Este control
# repite el barrido con n=300 y n=1200 (4x de diferencia en memoria) y compara
# las curvas normalizadas. Corre menos veces que el barrido principal porque
# lo que se compara es la FORMA de la curva, no un tiempo preciso.

E3C_NS = [300, 1200]
E3C_SEMILLAS = 2
E3C_REPETICIONES = 3


def e3c(args):
    """E3c - Control: el codo de PD, ies por el tamano del arreglo?"""
    experimento = "e3c_control_codo"
    hechas = leer_hechas(experimento, E3C_REPETICIONES)
    f, escritor = abrir_csv(experimento)

    print("E3c - control del codo de PD   (misma forma con n distinto?)")
    print(f"{'d':>4} |" + "".join(f"{('n=' + str(n)):>26}" for n in [E3_N_GRANDE] + E3C_NS))
    base = {}
    try:
        for d in E3_DS:
            linea = f"{d:>4} |"
            for n in [E3_N_GRANDE] + E3C_NS:
                k = n // 2
                reps = REPETICIONES if n == E3_N_GRANDE else E3C_REPETICIONES
                sems = E3_SEMILLAS if n == E3_N_GRANDE else E3C_SEMILLAS
                exp = "e3_barrido_d" if n == E3_N_GRANDE else experimento
                hech = leer_hechas(exp, reps) if n == E3_N_GRANDE else hechas
                medianas = []
                for semilla in range(sems):
                    m = medir_celda(escritor, exp, "pd", "cpp", BINARIO_CPP,
                                    "aleatoria", n, d, k, semilla, hech, reps)
                    if m in (None, -1.0):
                        break
                    if m != "ya":
                        medianas.append(m)
                f.flush()
                if medianas:
                    m = statistics.median(medianas)
                    base.setdefault(n, m)
                    kb = n * d * 8 / 1024
                    linea += f"{m:>10.1f}ms x{m/base[n]:<5.2f}{kb:>7.0f}KB"
                else:
                    linea += f"{'(ya medido)':>26}"
            print(linea)
    finally:
        f.close()
    print("\nSi las columnas normalizadas (xN) coinciden pese a que la memoria")
    print("cambia 4x, el codo NO es por el tamano del arreglo.")
    print(f"\nResultados crudos en {os.path.relpath(RESULTADOS, RAIZ)}/{experimento}.csv")


# ---------------------------------------------------------------------------
# E4 - La estructura de la musica (aleatoria vs repetitiva)
# ---------------------------------------------------------------------------

# Multiplos de 6, que es el largo del patron ABBCBB.
E4_TAMANOS = [12, 18, 24, 30, 36, 48, 60, 90, 120, 180, 240, 300, 420, 600,
              900, 1200, 1800, 2400]
E4_FAMILIAS = ["aleatoria", "estructurada_r0.02", "estructurada"]
E4_SEMILLAS = 5


def e4(args):
    """E4 - Cuanto cambia que la musica sea repetitiva.

    HIPOTESIS. Toda la premisa del recorte consciente es que una cancion repite
    secciones: si el estribillo vuelve a sonar igual, cortar de una repeticion a
    la otra es inaudible. En una instancia con secciones repetidas EXISTEN saltos
    que cuestan (casi) cero, asi que backtracking deberia encontrar temprano una
    solucion muy buena y podar mucho mas que en material aleatorio. Para FB no
    deberia cambiar nada, porque su trabajo lo fijan n y k y no mira los numeros.
    Para PD tampoco: llena la misma tabla pase lo que pase.

    SE VARIA        n, y la familia de la instancia (3 familias)
    SE CONTROLA     d=12, k=n/2, semillas 0..4
    SE MIDE         nodos explorados y tiempo
    """
    experimento = "e4_estructura"
    hechas = leer_hechas(experimento)
    f, escritor = abrir_csv(experimento)

    usar_instr = os.path.exists(BINARIO_INSTR)
    vivos = {(alg, fam): True for alg in ("fb", "bt", "pd") for fam in E4_FAMILIAS}

    print(f"E4 - estructura de los datos   (d=12, k=n/2, {E4_SEMILLAS} instancias x {REPETICIONES} corridas)")
    print(f"{'n':>6} | {'BT aleatoria':>22} {'BT +ruido 0,02':>22} {'BT repetitiva':>22} | {'nodos FB':>12}")
    print("-" * 92)

    try:
        for n in E4_TAMANOS:
            k = max(2, n // 2)
            celda, nodos = {}, {}
            for alg in ("bt", "fb", "pd"):
                for fam in E4_FAMILIAS:
                    if not vivos[(alg, fam)]:
                        celda[(alg, fam)] = "--"
                        continue
                    binario = BINARIO_INSTR if (usar_instr and alg in ("fb", "bt")) else BINARIO_CPP
                    medianas, nods = [], []
                    for semilla in range(E4_SEMILLAS):
                        m = medir_celda(escritor, experimento, alg, "cpp", binario,
                                        fam, n, 12, k, semilla, hechas)
                        if m == -1.0 or m is None:
                            vivos[(alg, fam)] = False
                            break
                        if m != "ya":
                            medianas.append(m)
                        r = correr(binario, alg, instancia(fam, n, 12, k, semilla))
                        if r and r["nodos"] != "":
                            nods.append(r["nodos"])
                    f.flush()
                    if not vivos[(alg, fam)]:
                        celda[(alg, fam)] = f">{LIMITE_SEGUNDOS:.0f}s"
                    elif medianas:
                        celda[(alg, fam)] = f"{statistics.median(medianas):,.3f} ms"
                    else:
                        celda[(alg, fam)] = "(ya)"
                    nodos[(alg, fam)] = int(statistics.median(nods)) if nods else 0

            def col(fam):
                nod = nodos.get(("bt", fam), 0)
                return f"{celda[('bt', fam)]:>11} {nod:>10,}"
            fbn = nodos.get(("fb", "aleatoria"), 0)
            print(f"{n:>6} | {col('aleatoria')} {col('estructurada_r0.02')} "
                  f"{col('estructurada')} | {fbn:>12,}")
    finally:
        f.close()

    print()
    print("Si los nodos de BT en la columna 'repetitiva' valen n-3, el algoritmo")
    print("exponencial se volvio LINEAL. Ver e4r para saber que tan fragil es eso.")
    print(f"\nResultados crudos en {os.path.relpath(RESULTADOS, RAIZ)}/{experimento}.csv")


# E4r - Cuan exacta tiene que ser la repeticion
#
# En E4 el material perfectamente repetitivo hace que BT colapse a lineal. Pero
# un estribillo real NO vuelve a sonar identico: hay variacion de interpretacion,
# de mezcla, de ruido de fondo. La pregunta es si el colapso sobrevive a esa
# imperfeccion o si se cae al primer decimal.
#
# OJO: el generador escribe 4 decimales, asi que un ruido por debajo de ~0,00005
# se redondea a cero y la instancia vuelve a ser exactamente repetitiva. Por eso
# el barrido arranca en 0,0001 y el 0 va aparte.

E4R_RUIDOS = [0.0, 0.0001, 0.0005, 0.001, 0.005, 0.02, 0.1, 0.5]
E4R_N, E4R_K = 24, 12


def e4r(args):
    """E4r - Cuanta imperfeccion tolera el colapso de backtracking."""
    experimento = "e4r_tolerancia_ruido"
    hechas = leer_hechas(experimento)
    f, escritor = abrir_csv(experimento)

    print(f"E4r - cuan exacta tiene que ser la repeticion   (n={E4R_N}, k={E4R_K}, d=12)")
    print(f"{'ruido':>10} | {'nodos BT: las 5 semillas':>34} | {'mediana':>8} | {'costo opt':>10}")
    print("-" * 74)
    try:
        for ruido in E4R_RUIDOS + [None]:
            fam = ("aleatoria" if ruido is None else
                   "estructurada" if ruido == 0.0 else f"estructurada_r{ruido}")
            nods, costos = [], []
            for semilla in range(E4_SEMILLAS):
                medir_celda(escritor, experimento, "bt", "cpp", BINARIO_INSTR,
                            fam, E4R_N, 12, E4R_K, semilla, hechas)
                r = correr(BINARIO_INSTR, "bt", instancia(fam, E4R_N, 12, E4R_K, semilla))
                if r:
                    nods.append(r["nodos"]); costos.append(r["costo"])
            f.flush()
            etiqueta = "aleatoria" if ruido is None else f"{ruido:g}"
            print(f"{etiqueta:>10} | {str(sorted(nods)):>34} | "
                  f"{int(statistics.median(nods)):>8,} | {statistics.median(costos):>10.4f}")
    finally:
        f.close()
    print(f"\nResultados crudos en {os.path.relpath(RESULTADOS, RAIZ)}/{experimento}.csv")


# E4k - Control: no alcanza con que la musica se repita
#
# E4 mide todo con k = n/2 y ahi el material repetitivo hace que BT colapse a
# n-3 nodos. Pero eso NO es una propiedad de la repeticion sola: depende de que
# la cantidad de pulsos pedida caiga donde estan los cortes gratis.
#
# En el patron ABBCBB los bloques repetidos permiten cortar sin costo, pero solo
# para ciertos largos. Si el k pedido no coincide con ninguno de esos largos, el
# optimo deja de valer 0 y backtracking vuelve a explotar. Este control barre k
# midiendo las dos cosas a la vez: el costo optimo (con PD, que siempre lo
# encuentra) y los nodos de BT.

E4K_N = 120
E4K_FRACCIONES = [0.25, 1/3, 0.4, 0.5, 0.6, 2/3, 0.75, 5/6, 1.0]


def e4k(args):
    """E4k - Control: el colapso depende de k, no solo de la repeticion."""
    experimento = "e4k_colapso_segun_k"
    hechas = leer_hechas(experimento)
    f, escritor = abrir_csv(experimento)
    n = E4K_N

    print(f"E4k - por que el colapso depende de k   (n={n}, d=12, material repetitivo exacto)")
    print(f"{'k':>5} {'k/n':>6} | {'costo optimo':>13} {'corte gratis':>13} | "
          f"{'nodos BT (mediana)':>19} {'= n-3':>7}")
    print("-" * 76)
    try:
        for frac in E4K_FRACCIONES:
            k = max(2, round(n * frac))
            nods, costos = [], []
            for semilla in range(E4_SEMILLAS):
                for alg, binario in (("pd", BINARIO_CPP), ("bt", BINARIO_INSTR)):
                    medir_celda(escritor, experimento, alg, "cpp", binario,
                                "estructurada", n, 12, k, semilla, hechas)
                r = correr(BINARIO_INSTR, "bt", instancia("estructurada", n, 12, k, semilla))
                p = correr(BINARIO_CPP, "pd", instancia("estructurada", n, 12, k, semilla))
                if r:
                    nods.append(r["nodos"])
                if p:
                    costos.append(p["costo"])
            f.flush()
            c = statistics.median(costos)
            nod = int(statistics.median(nods))
            print(f"{k:>5} {frac:>6.2f} | {c:>13.4f} {('SI' if c == 0 else 'no'):>13} | "
                  f"{nod:>19,} {('SI' if nod == n - 3 else 'no'):>7}")
    finally:
        f.close()
    print()
    print("Leer las dos columnas juntas: donde el optimo vale 0 backtracking es")
    print("chico, y donde no vale 0 explota. La repeticion sola no alcanza.")
    print(f"\nResultados crudos en {os.path.relpath(RESULTADOS, RAIZ)}/{experimento}.csv")


# ---------------------------------------------------------------------------
# E5 - Audio real: el caso de uso, de punta a punta
# ---------------------------------------------------------------------------
#
# Los otros experimentos miden sobre instancias que fabricamos nosotros. Este
# mide sobre instancias que salieron de un archivo de audio pasando por el
# pipeline completo: sintesis o grabacion -> wav -> librosa -> cromas -> .txt.
#
# Las instancias estan VERSIONADAS en input/, asi que este experimento corre sin
# instalar librosa. Para regenerarlas o agregar grabaciones propias:
#
#     python3 -m venv .venv && .venv/bin/pip install -r python/requirements.txt
#     .venv/bin/python python/generar_demo.py --salida audio/demo_largo.wav --compases 15
#     .venv/bin/python python/extraer.py audio/demo_largo.wav --salida input/demo_largo --duracion 150
#
# HIPOTESIS. E4 mostro que la musica repetitiva derrumba el arbol de
# backtracking. Una cancion ES repetitiva, asi que BT deberia andar bien. Pero
# el control e4r mostro que el colapso exige repeticion EXACTA, y una grabacion
# real nunca repite exacta. La pregunta es cual de los dos efectos gana.

E5_INSTANCIAS = [
    ("demo",       "pieza sintetizada A B B C B B, 24 s"),
    ("demo_largo", "la misma pieza a largo de cancion, 3 min"),
]
E5_FRACCIONES = [0.08, 0.25, 0.50, 0.70, 0.83, 0.95]


def e5(args):
    """E5 - Audio real: los tres algoritmos sobre instancias extraidas de audio.

    SE VARIA        la grabacion, y k
    SE CONTROLA     d = 12 (cromas, lo que devuelve extraer.py)
    SE MIDE         tiempo, nodos y costo del optimo
    """
    experimento = "e5_audio_real"
    hechas = leer_hechas(experimento)
    f, escritor = abrir_csv(experimento)
    usar_instr = os.path.exists(BINARIO_INSTR)

    print("E5 - audio real   (instancias extraidas con extraer.py, d=12 cromas)")
    try:
        for nombre, desc in E5_INSTANCIAS:
            ruta = os.path.join(TP1, "input", nombre + ".txt")
            if not os.path.exists(ruta):
                print(f"\n  [{nombre}] no esta en input/, se saltea. Ver la cabecera de e5().")
                continue
            with open(ruta) as fh:
                n, d, _ = (int(x) for x in fh.readline().split())
            print(f"\n  {nombre}: {desc}")
            print(f"  n = {n} pulsos, d = {d}")
            print(f"  {'k':>6} {'k/n':>6} | {'FB':>13} {'BT':>13} {'PD':>11} | {'nodos BT':>12}")
            print("  " + "-" * 74)
            for frac in E5_FRACCIONES:
                k = max(2, min(n, round(n * frac)))
                # La instancia ya existe: se reescribe solo la primera linea
                # para cambiar k, sin tocar las caracteristicas.
                with open(ruta) as fh:
                    cuerpo = fh.readlines()[1:]
                tmp = os.path.join(TRABAJO, f"audio_{nombre}_k{k}.txt")
                os.makedirs(TRABAJO, exist_ok=True)
                with open(tmp, "w") as fh:
                    fh.write(f"{n} {d} {k}\n")
                    fh.writelines(cuerpo)
                celda, nodos = {}, 0
                for alg in ("fb", "bt", "pd"):
                    binario = BINARIO_INSTR if (usar_instr and alg in ("fb", "bt")) else BINARIO_CPP
                    arranque = time.perf_counter()
                    sonda = correr(binario, alg, tmp, tope=LIMITE_SEGUNDOS * 1.5)
                    transcurrido = time.perf_counter() - arranque
                    if sonda is None or transcurrido > LIMITE_SEGUNDOS:
                        celda[alg] = f">{LIMITE_SEGUNDOS:.0f}s"
                        continue
                    filas, tiempos = [], []
                    for r in range(1, REPETICIONES + 1):
                        res = correr(binario, alg, tmp) if r > 1 else sonda
                        if res is None:
                            break
                        tiempos.append(res["ms"])
                        fila = dict(experimento=experimento, algoritmo=alg, implementacion="cpp",
                                    familia="audio:" + nombre, n=n, d=d, k=k, semilla=0, repeticion=r)
                        fila.update(res)
                        filas.append(fila)
                    for fila in filas:
                        escritor.writerow(fila)
                    celda[alg] = f"{statistics.median(tiempos):,.2f} ms" if tiempos else "--"
                    if alg == "bt" and sonda.get("nodos") not in ("", None):
                        nodos = sonda["nodos"]
                f.flush()
                print(f"  {k:>6} {frac:>6.2f} | {celda['fb']:>13} {celda['bt']:>13} "
                      f"{celda['pd']:>11} | {nodos:>12,}")
    finally:
        f.close()
    print(f"\nResultados crudos en {os.path.relpath(RESULTADOS, RAIZ)}/{experimento}.csv")


# ---------------------------------------------------------------------------
# E6 - Ablacion de podas: cuanto aporta cada una
# ---------------------------------------------------------------------------
#
# Los binarios de este experimento salen de los MISMOS fuentes que radioedit:
# la unica diferencia son dos #ifdef que apagan una poda cada uno. Asi la
# comparacion no mezcla cambios de codigo con cambios de poda.
#
#     make ablacion
#
# Tamanos: aleatoria barre de 10 a 24. La variante sin podas visita el arbol
# entero de fuerza bruta, asi que muere en el mismo n que FB y no tiene sentido
# ir mas arriba. Las estructuradas son multiplos de 6 porque el patron ABBCBB
# tiene 6 secciones.

E6_TAMANOS = [10, 12, 14, 16, 18, 20, 22, 24]
E6_TAMANOS_EST = [12, 18, 24, 30, 36]

# clave, binario, etiqueta para la tabla
E6_VARIANTES = [
    ("ambas",      BINARIO_INSTR,                                   "ambas"),
    ("sin_opt",    os.path.join(TP1, "radioedit_sin_opt"),           "solo fact."),
    ("sin_fact",   os.path.join(TP1, "radioedit_sin_fact"),          "solo optim."),
    ("sin_podas",  os.path.join(TP1, "radioedit_sin_podas"),         "ninguna"),
]


def e6(args):
    """E6 - Ablacion de podas: cuanto aporta cada poda de backtracking.

    Backtracking es fuerza bruta mas dos if. Hasta aca el informe dice que tiene
    dos podas, pero nunca muestra cuanto aporta cada una. Este experimento las
    apaga de a una y mide que se pierde.

    HIPOTESIS. La poda por optimalidad es la que hace el trabajo pesado: corta
    ramas mirando el COSTO, que es justamente lo que fuerza bruta nunca hace. La
    de factibilidad solo descarta ramas que ya no llegan a k elegidos, y el caso
    base las detecta igual unos niveles mas abajo, asi que deberia aportar poco.

    PREDICCION QUE FALSA EL EXPERIMENTO SI SALE MAL. Con las dos podas apagadas,
    backtracking tiene que visitar EXACTAMENTE los mismos nodos que fuerza
    bruta: es el mismo arbol de decision sin ningun corte. Si esos dos numeros
    no coinciden, entonces los algoritmos no comparten el arbol que decimos que
    comparten, y toda la comparacion de E2 estaria mal planteada.

    SE VARIA        que podas estan activas (4 configuraciones) y n
    SE CONTROLA     d=12, k=n/2, semillas 0..2
    SE MIDE         nodos visitados, tiempo y disparos de cada poda
    """
    experimento = "e6_ablacion_podas"
    faltan = [b for _, b, _ in E6_VARIANTES if not os.path.exists(b)]
    if faltan:
        raise SystemExit("Faltan los binarios de ablacion. Corre 'make ablacion' desde TP1/.\n"
                         + "\n".join("  " + b for b in faltan))

    hechas = leer_hechas(experimento)
    f, escritor = abrir_csv(experimento)

    def barrer(familia, tamanos, titulo):
        """Un barrido de n para una familia. Devuelve los nodos medidos."""
        print(f"\n{titulo}")
        cab = " ".join(f"{e:>13}" for _, _, e in E6_VARIANTES)
        print(f"{'n':>5} {'k':>4} |{cab} | {'FB':>13} | {'=FB?':>5}")
        print("-" * (24 + 14 * len(E6_VARIANTES) + 24))
        vivos = {clave: True for clave, _, _ in E6_VARIANTES}
        vivos["fb"] = True
        recogido = {}

        for n in tamanos:
            k = max(2, n // 2)
            nodos, celda = {}, {}

            for clave, binario, _ in E6_VARIANTES:
                if not vivos[clave]:
                    celda[clave] = "--"
                    continue
                nods, muerto = [], False
                for semilla in range(SEMILLAS):
                    m = medir_celda(escritor, experimento, "bt", "cpp_" + clave, binario,
                                    familia, n, 12, k, semilla, hechas)
                    if m == -1.0 or m is None:
                        muerto = True
                        break
                    r = correr(binario, "bt", instancia(familia, n, 12, k, semilla),
                               tope=LIMITE_SEGUNDOS * 1.5)
                    if r and r["nodos"] != "":
                        nods.append(r["nodos"])
                if muerto:
                    vivos[clave] = False
                    celda[clave] = f">{LIMITE_SEGUNDOS:.0f}s"
                    continue
                nodos[clave] = int(statistics.median(nods)) if nods else 0
                celda[clave] = f"{nodos[clave]:,}"

            # Fuerza bruta como referencia: es el arbol entero, sin podar.
            nodos_fb = 0
            if vivos["fb"]:
                nods = []
                for semilla in range(SEMILLAS):
                    m = medir_celda(escritor, experimento, "fb", "cpp", BINARIO_INSTR,
                                    familia, n, 12, k, semilla, hechas)
                    if m == -1.0 or m is None:
                        vivos["fb"] = False
                        break
                    r = correr(BINARIO_INSTR, "fb", instancia(familia, n, 12, k, semilla),
                               tope=LIMITE_SEGUNDOS * 1.5)
                    if r and r["nodos"] != "":
                        nods.append(r["nodos"])
                nodos_fb = int(statistics.median(nods)) if nods else 0
            f.flush()

            # El chequeo que hace falsable al experimento.
            coincide = "-"
            if nodos_fb and "sin_podas" in nodos:
                coincide = "SI" if nodos["sin_podas"] == nodos_fb else "NO"
            recogido[n] = dict(nodos, fb=nodos_fb)

            fila = " ".join(f"{celda[c]:>13}" for c, _, _ in E6_VARIANTES)
            print(f"{n:>5} {k:>4} |{fila} | {(f'{nodos_fb:,}' if nodos_fb else '--'):>13} | {coincide:>5}")
        return recogido

    try:
        print(f"E6 - ablacion de podas   (d=12, k=n/2, {SEMILLAS} instancias x {REPETICIONES} corridas)")
        print("Nodos visitados por backtracking segun que podas esten activas.")
        alea = barrer("aleatoria", E6_TAMANOS,
                      "(a) Instancias aleatorias: el caso adverso, casi ningun salto sale barato")
        estr = barrer("estructurada", E6_TAMANOS_EST,
                      "(b) Instancias repetitivas: el caso de E4, donde BT colapsa")
    finally:
        f.close()

    # Cuanto aporta cada poda, en el n mas grande que sobrevivio con las dos.
    print("\nAPORTE DE CADA PODA (factor de reduccion contra no podar nada)")
    print(f"{'familia':>14} {'n':>5} | {'solo fact.':>12} {'solo optim.':>12} {'ambas':>12}")
    print("-" * 62)
    for nombre, datos in (("aleatoria", alea), ("repetitiva", estr)):
        candidatos = [n for n, v in datos.items() if v.get("sin_podas") and v.get("ambas")]
        if not candidatos:
            continue
        n = max(candidatos)
        base = datos[n]["sin_podas"]
        def factor(clave):
            v = datos[n].get(clave)
            return f"{base / v:,.1f}x" if v else "--"
        print(f"{nombre:>14} {n:>5} | {factor('sin_opt'):>12} {factor('sin_fact'):>12} "
              f"{factor('ambas'):>12}")

    print("\nLa columna '=FB?' es el chequeo: sin ninguna poda, backtracking tiene que")
    print("visitar el mismo arbol que fuerza bruta. Si dice NO, hay un problema.")
    print(f"\nResultados crudos en {os.path.relpath(RESULTADOS, RAIZ)}/{experimento}.csv")


# ---------------------------------------------------------------------------
# E7 - C++ contra Python: cuanto cuesta el lenguaje
# ---------------------------------------------------------------------------
#
# El instructivo pide comparar "las distintas implementaciones", y el punto 2 del
# enunciado pide portar los algoritmos a Python. Este experimento une las dos
# cosas: mide el MISMO algoritmo sobre la MISMA instancia en los dos lenguajes.
#
# La comparacion es justa porque los dos ports pasan los mismos 223 chequeos
# (python3 python/tests.py --binario python/main.py): estan resolviendo el mismo
# problema con la misma estructura, no dos programas parecidos.

E7_TAMANOS = [10, 12, 14, 16, 18, 20, 22, 24, 26, 30, 40, 60, 100, 150, 200, 300]


def e7(args):
    """E7 - Cuanto se paga por escribir el mismo algoritmo en Python.

    HIPOTESIS. Python va a ser mas lento en los tres, eso no es noticia. La
    pregunta es si el factor es UNO SOLO -una constante del lenguaje que se
    pueda enunciar como "Python es N veces mas lento"- o si depende del
    algoritmo. Si depende, el factor mide algo mas interesante: cuanto del
    trabajo de cada algoritmo es interpretable y cuanto es cuenta pura.

    SE VARIA        la implementacion (C++ / Python) y n
    SE CONTROLA     d=12, k=n/2, instancias aleatorias, semillas 0..2
    SE MIDE         tiempo de resolver(), en ms
    """
    experimento = "e7_cpp_vs_python"
    hechas = leer_hechas(experimento)
    f, escritor = abrir_csv(experimento)
    vivos = {(alg, impl): True for alg in ("fb", "bt", "pd") for impl in ("cpp", "py")}

    print(f"E7 - C++ contra Python   (d=12, k=n/2, {SEMILLAS} instancias x {REPETICIONES} corridas)")
    print(f"{'n':>5} {'k':>5} | {'FB c++':>11} {'FB py':>11} {'x':>7} | "
          f"{'BT c++':>11} {'BT py':>11} {'x':>7} | {'PD c++':>11} {'PD py':>11} {'x':>7}")
    print("-" * 116)

    try:
        for n in E7_TAMANOS:
            k = max(2, n // 2)
            if not any(vivos.values()):
                break
            med = {}
            for alg in ("fb", "bt", "pd"):
                for impl, binario in (("cpp", BINARIO_CPP), ("py", BINARIO_PY)):
                    if not vivos[(alg, impl)]:
                        med[(alg, impl)] = None
                        continue
                    medianas = []
                    for semilla in range(SEMILLAS):
                        m = medir_celda(escritor, experimento, alg, impl, binario,
                                        "aleatoria", n, 12, k, semilla, hechas)
                        if m == -1.0 or m is None:
                            vivos[(alg, impl)] = False
                            break
                        if m != "ya":
                            medianas.append(m)
                    med[(alg, impl)] = statistics.median(medianas) if medianas else None
            f.flush()

            def col(alg):
                c, p = med.get((alg, "cpp")), med.get((alg, "py"))
                def t(v, vivo):
                    if v is not None:
                        return f"{v:,.3f}"
                    return "--" if not vivo else "(ya)"
                razon = f"{p / c:,.0f}x" if (c and p) else "--"
                return (f"{t(c, vivos[(alg,'cpp')]):>11} {t(p, vivos[(alg,'py')]):>11} "
                        f"{razon:>7}")

            print(f"{n:>5} {k:>5} | {col('fb')} | {col('bt')} | {col('pd')}")
    finally:
        f.close()

    print()
    print("Si la columna 'x' fuera parecida en los tres, el factor seria del lenguaje.")
    print("Si no, mide cuanto del trabajo de cada algoritmo es interpretable.")
    print(f"\nResultados crudos en {os.path.relpath(RESULTADOS, RAIZ)}/{experimento}.csv")


# ---------------------------------------------------------------------------
# E8 - Cuanto cuesta recortar, y de que depende
# ---------------------------------------------------------------------------
#
# Los otros siete experimentos miden TIEMPO y NODOS: cuanto tarda cada
# algoritmo. Ninguno mide si el recorte que sale es BUENO. Este mide eso, y es
# el unico que habla del problema en vez de hablar de los algoritmos.
#
# Solo usa programacion dinamica, que tarda milisegundos, asi que barrer k sale
# gratis. No hace falta ningun binario nuevo ni tocar una linea de C++.
#
# OJO CON LA HIPOTESIS ORIGINAL. Arrancamos buscando un "codo": un punto a
# partir del cual recortar empieza a doler. Con k de 10 % en 10 % no aparecio
# ningun codo y las curvas salieron irregulares. Barriendo de a UN pulso se
# entendio por que: el costo no depende de CUANTO se descarta sino de si lo
# descartado es un numero entero de COMPASES. Muestrear de a 10 % estaba
# tomando la oscilacion en fases arbitrarias.

# De a un pulso. El primer tramo -1 a 48- son 12 compases de 4/4: alcanza para
# ver tres periodos completos del patron de 16 y sigue siendo un barrido chico.
# El segundo tramo mira si el efecto sigue vivo con recortes grandes; incluye el
# descarte de 71 pulsos, que es el recorte al 75 % que se escucho en E5.
E8_DESCARTES = list(range(1, 49)) + list(range(64, 85))

# Pulsos por compas. En 4/4 -que es lo que toca todo este material- son 4.
E8_COMPAS = 4

# Periodos a probar en la segunda tabla. No se asume que sea 4: se prueban
# varios y cada grabacion dice cual es el suyo.
E8_PERIODOS = [2, 3, 4, 6, 8, 12, 16]

# Ordenadas por que tan rigida es la grilla temporal, que es lo que resulto
# importar. Las dos primeras estan hechas con secuenciador; las tres ultimas las
# toca o las habla una persona.
E8_GRABACIONES = [
    ("propias/cancion",     "reggaetón (Tití Me Preguntó)",   "grilla rígida"),
    ("propias/electronica", "electrónica (Around the World)", "grilla rígida"),
    ("demo_largo",          "sintetizada A B B C B B",        "grilla exacta"),
    ("librosa/fishin",      "folk estrofa/estribillo",        "tocada a mano"),
    ("librosa/brahms",      "clásica con rubato",             "tempo elástico"),
    ("librosa/libri1",      "narración hablada",              "sin ritmo"),
]


def leer_instancia(ruta):
    """Devuelve (n, d, features). features queda 0-based, como en el C++."""
    with open(ruta) as f:
        n, d, _ = (int(x) for x in f.readline().split())
        features = [[float(x) for x in f.readline().split()] for _ in range(n)]
    return n, d, features


def corte_unico(features, n, k):
    """El mejor recorte que hace UN SOLO corte: quedarse con los primeros i
    pulsos, saltar, y quedarse con la cola. Es lo que haria alguien a mano.

    Descarta n-k pulsos seguidos, asi que el salto va del pulso i al i+(n-k)+1 y
    cuesta c(i,j) = ||f_{i+1} - f_j||. Probar los k-1 cortes posibles es O(n*d):
    al lado de cualquiera de los tres algoritmos, no cuesta nada.

    Sirve de piso. Si el optimo no le gana por mucho, entonces lo que aportan
    los algoritmos exactos no es un recorte mejor sino la GARANTIA de que no hay
    ninguno mejor. Es una conclusion incomoda y hay que poder decirla."""
    descartar = n - k
    if descartar <= 0:
        return 0.0
    mejor = None
    for i in range(1, k):
        j = i + descartar + 1
        # c(i,j) con la indexacion 1-based del TP: f_{i+1} es features[i].
        suma = 0.0
        a, b = features[i], features[j - 1]
        for m in range(len(a)):
            dif = a[m] - b[m]
            suma += dif * dif
        c = math.sqrt(suma)
        if mejor is None or c < mejor:
            mejor = c
    return mejor


def e8(args):
    """E8 - Cuanto cuesta recortar una grabacion, y de que depende.

    HIPOTESIS (la corregida, despues de la sonda; ver la nota de arriba).
    El costo del recorte optimo no lo decide cuanto se recorta sino DONDE se
    puede pegar el corte. En musica hecha con secuenciador los pulsos caen en
    una grilla exacta y la musica se repite cada 4 pulsos, asi que descartar un
    numero entero de compases deberia salir mucho mas barato que descartar
    cualquier otra cantidad. En musica tocada por una persona el tempo respira,
    la grilla no es exacta, y el efecto deberia desaparecer.

    PREDICCION QUE PUEDE SALIR MAL. Si el efecto apareciera tambien en la
    narracion hablada -que no tiene ritmo ninguno- entonces no seria musical y
    habria que buscar la causa en el extractor de caracteristicas.

    SE VARIA        cuantos pulsos se descartan (de 1 a 48, de a uno) y la grabacion
    SE CONTROLA     d = 12 (cromas, lo que devuelve extraer.py)
    SE MIDE         costo del optimo, y costo del mejor corte unico
    """
    experimento = "e8_cuanto_recortar"
    f, escritor = abrir_csv(experimento)
    resumen = []

    print("E8 - cuanto cuesta recortar, y de que depende")
    print(f"Costo del recorte optimo descartando de a un pulso. Compas = {E8_COMPAS} pulsos.\n")
    print(f"  {'grabacion':<14} {'grilla':<16} {'n':>5} | "
          f"{'compas entero':>14} {'resto':>9} {'ratio':>7} | {'corte unico':>12}")
    print("  " + "-" * 88)
    try:
        for nombre, desc, grilla in E8_GRABACIONES:
            ruta = os.path.join(TP1, "input", nombre + ".txt")
            if not os.path.exists(ruta):
                print(f"  [{nombre}] no esta en input/, se saltea.")
                continue
            corto = os.path.basename(nombre)
            costos = {}
            n, d, features = leer_instancia(ruta)
            cuerpo = open(ruta).read().split("\n", 1)[1]

            dentro, fuera, iguales, total = [], [], 0, 0

            for descartar in E8_DESCARTES:
                # Con n chico no se puede descartar mucho sin quedarse sin
                # grabacion: se corta en un tercio.
                if descartar > max(4, n // 3):
                    continue
                k = n - descartar
                if k < 2:
                    continue
                tmp = os.path.join(TRABAJO, f"e8_{corto}_d{descartar}.txt")
                os.makedirs(TRABAJO, exist_ok=True)
                with open(tmp, "w") as fh:
                    fh.write(f"{n} {d} {k}\n")
                    fh.write(cuerpo)

                # PD es exacta y determinista: el costo no cambia entre corridas.
                # Las repeticiones son para el tiempo, que aca no es el punto.
                filas = []
                for r in range(1, REPETICIONES + 1):
                    res = correr(BINARIO_CPP, "pd", tmp)
                    if res is None:
                        break
                    fila = dict(experimento=experimento, algoritmo="pd", implementacion="cpp",
                                familia="audio:" + corto, n=n, d=d, k=k, semilla=0, repeticion=r)
                    fila.update(res)
                    filas.append(fila)
                if not filas:
                    continue
                optimo = filas[0]["costo"]
                unico = corte_unico(features, n, k)
                for fila in filas:
                    escritor.writerow(fila)
                # La heuristica va al mismo CSV con su propio nombre de algoritmo:
                # asi la figura la lee igual que a las demas, sin caso especial.
                escritor.writerow(dict(
                    experimento=experimento, algoritmo="corte_unico", implementacion="python",
                    familia="audio:" + corto, n=n, d=d, k=k, semilla=0, repeticion=1,
                    ms="", costo=unico, nodos="", poda_fact="", poda_opt=""))

                costos[descartar] = optimo
                (dentro if descartar % E8_COMPAS == 0 else fuera).append(optimo)
                total += 1
                if abs(unico - optimo) < 1e-9:
                    iguales += 1
            f.flush()

            if not dentro or not fuera:
                continue
            md, mf = statistics.median(dentro), statistics.median(fuera)
            ratio = mf / md if md > 1e-12 else float("inf")
            marca = "  <<<" if ratio > 1.5 else ""
            resumen.append((corto, grilla, costos))
            print(f"  {corto:<14} {grilla:<16} {n:>5} | {md:>14.4f} {mf:>9.4f} "
                  f"{ratio:>6.2f}x | {iguales:>4}/{total:<3} iguales{marca}")
    finally:
        f.close()

    # Segunda mitad: el compas de 4 es una suposicion nuestra. Esta tabla la
    # saca, y deja que cada grabacion diga con que periodo repite. Es lo que
    # convierte el resultado en una medicion y no en una corazonada: la pieza
    # sintetizada tiene que responder al periodo que dice su propio codigo.
    print()
    print("A QUE PERIODO RESPONDE CADA GRABACION")
    print("Ratio entre el costo tipico y el costo cuando se descarta un multiplo del periodo.")
    print(f"  {'grabacion':<14}" + "".join(f"{p:>8}" for p in E8_PERIODOS))
    print("  " + "-" * (14 + 8 * len(E8_PERIODOS)))
    for corto, grilla, costos in resumen:
        fila = f"  {corto:<14}"
        for periodo in E8_PERIODOS:
            dentro = [c for dd, c in costos.items() if dd % periodo == 0]
            fuera = [c for dd, c in costos.items() if dd % periodo != 0]
            if len(dentro) < 3 or not fuera:
                fila += f"{'--':>8}"
                continue
            fila += f"{statistics.median(fuera) / statistics.median(dentro):>7.2f}x"
        print(fila)
    print()
    print("Un ratio alto en la columna P dice que descartar un multiplo de P pulsos")
    print("sale barato: P es el periodo con el que esa grabacion se repite.")

    print()
    print("'compas entero' es la mediana del costo cuando lo descartado es multiplo")
    print(f"de {E8_COMPAS} pulsos; 'resto', cuando no lo es. Si el ratio es alto, lo que")
    print("decide el costo no es CUANTO se recorta sino si el recorte cae en la grilla.")
    print("'iguales' cuenta en cuantos casos el mejor corte unico YA ES el optimo.")
    print(f"\nResultados crudos en {os.path.relpath(RESULTADOS, RAIZ)}/{experimento}.csv")


# ---------------------------------------------------------------------------
# E9 - Canciones reales: que algoritmo sirve para recortarlas
# ---------------------------------------------------------------------------
#
# El experimento mas simple del trabajo, pensado para leerse sin contexto: se
# toman grabaciones REALES, se pide el recorte de un radio edit tipico (conservar
# el 75 % de los pulsos, que es el k que ya traen los archivos) y se mira cual de
# los tres algoritmos termina dentro del limite de 10 segundos.
#
# Las ocho de input/librosa/ tienen licencia libre (vienen con librosa) y las
# dos de input/propias/ son canciones del grupo recortadas a 3 minutos. Queda
# afuera humpback (canto de ballena): es audio real pero no es musica.
#
# HIPOTESIS. Solo programacion dinamica deberia terminar en las grabaciones de
# largo de cancion. Fuerza bruta solo en la mas corta, y backtracking en algunas
# si, en otras no, segun el material.

E9_GRABACIONES = [
    ("librosa/libri1",     "Voz hablada (lectura de un libro)"),
    ("librosa/choice",     "Drum & bass"),
    ("librosa/brahms",     "Clásica: Danza húngara n.º 5 (Brahms)"),
    ("librosa/sweetwaltz", "Vals"),
    ("librosa/pistachio",  "Ragtime"),
    ("librosa/nutcracker", "Clásica: Danza del hada de azúcar (Tchaikovsky)"),
    ("librosa/fishin",     "Folk con estrofa y estribillo"),
    ("propias/cancion",    "Reggaetón: Tití Me Preguntó (Bad Bunny)"),
    ("propias/electronica", "Electrónica: Around the World (Daft Punk)"),
]


def e9(args):
    """E9 - Canciones reales: los tres algoritmos recortando al 75 %.

    SE VARIA        la grabacion
    SE CONTROLA     d = 12 (cromas), k = 75 % de n, limite de 10 s
    SE MIDE         tiempo de cada algoritmo y costo del recorte
    """
    experimento = "e9_canciones_reales"
    hechas = leer_hechas(experimento)
    f, escritor = abrir_csv(experimento)

    print("E9 - canciones reales, recortadas al 75 %   (d=12 cromas, limite 10 s)\n")
    print(f"  {'grabacion':<22} {'n':>5} {'k':>5} | {'FB':>11} {'BT':>11} {'PD':>10} | {'costo':>7}")
    print("  " + "-" * 80)
    try:
        for nombre, desc in E9_GRABACIONES:
            ruta = os.path.join(TP1, "input", nombre + ".txt")
            if not os.path.exists(ruta):
                print(f"  [{nombre}] no esta en input/, se saltea.")
                continue
            with open(ruta) as fh:
                n, d, k = (int(x) for x in fh.readline().split())
            familia = "audio:" + nombre.split("/")[1]
            celda, costo = {}, None
            for alg in ("fb", "bt", "pd"):
                clave = (alg, "cpp", familia, str(n), str(d), str(k), "0")
                if clave in hechas:
                    celda[alg] = "ya medido"
                    continue
                arranque = time.perf_counter()
                sonda = correr(BINARIO_CPP, alg, ruta, tope=LIMITE_SEGUNDOS * 1.5)
                if sonda is None or time.perf_counter() - arranque > LIMITE_SEGUNDOS:
                    celda[alg] = f">{LIMITE_SEGUNDOS:.0f} s"
                    continue
                filas, tiempos = [], []
                for r in range(1, REPETICIONES + 1):
                    res = sonda if r == 1 else correr(BINARIO_CPP, alg, ruta)
                    if res is None:
                        break
                    tiempos.append(res["ms"])
                    fila = dict(experimento=experimento, algoritmo=alg, implementacion="cpp",
                                familia=familia, n=n, d=d, k=k, semilla=0, repeticion=r)
                    fila.update(res)
                    filas.append(fila)
                for fila in filas:
                    escritor.writerow(fila)
                f.flush()
                celda[alg] = f"{statistics.median(tiempos):,.2f} ms"
                costo = sonda["costo"]
            costo_txt = f"{costo:.4f}" if costo is not None else "--"
            print(f"  {nombre.split('/')[1]:<22} {n:>5} {k:>5} | {celda['fb']:>11} "
                  f"{celda['bt']:>11} {celda['pd']:>10} | {costo_txt:>7}")
    finally:
        f.close()
    print(f"\nResultados crudos en {os.path.relpath(RESULTADOS, RAIZ)}/{experimento}.csv")


EXPERIMENTOS = {
    "e1": ("Escalabilidad en n: donde deja de correr cada algoritmo", e1),
    "e2": ("Barrido de k: cuanto influye cuanto se recorta", e2),
    "e3": ("Barrido de d: cuanto pesa la cantidad de caracteristicas", e3),
    "e3c": ("Control de E3: de que depende el codo de PD", e3c),
    "e4": ("Estructura de los datos: musica repetitiva vs ruido", e4),
    "e4r": ("Control de E4: cuanta imperfeccion tolera el colapso", e4r),
    "e4k": ("Control de E4: por que el colapso depende de k", e4k),
    "e5": ("Audio real: el caso de uso de punta a punta", e5),
    "e6": ("Ablacion de podas: cuanto aporta cada una", e6),
    "e7": ("C++ contra Python: cuanto cuesta el lenguaje", e7),
    "e8": ("Cuanto cuesta recortar, y de que depende", e8),
    "e9": ("Canciones reales: que algoritmo sirve para recortarlas", e9),
}


# Los cuatro experimentos que aparecen en el informe, con el numero que tienen
# ahi. Son alias: el CSV de cada uno sigue llamandose como su experimento
# original (exp2 escribe e7_cpp_vs_python.csv, etc.).
INFORME = {
    "exp1": ("e1", "Hasta donde llega cada algoritmo", "unos 15-20 min"),
    "exp2": ("e7", "C++ contra Python", "unos 15-20 min"),
    "exp3": ("e6", "Que aporta cada poda (antes: make instrumentado ablacion)", "unos 2 min"),
    "exp4": ("e9", "Recortar canciones reales", "unos 7 min"),
}


def main():
    global RESULTADOS
    p = argparse.ArgumentParser(description="Experimentacion del TP1.")
    p.add_argument("experimento", nargs="*", help="cuales correr (ej: exp1, o e1)")
    p.add_argument("--lista", action="store_true", help="lista los experimentos")
    p.add_argument("--todos", "--informe", dest="todos", action="store_true",
                   help="corre los cuatro experimentos del informe (exp1 a exp4), desde cero")
    p.add_argument("--completo", action="store_true",
                   help="corre los 12 experimentos del script, incluidos los que no estan en el informe")
    p.add_argument("--nuevo", action="store_true",
                   help="mide desde cero en experimentos/resultados_nuevos/, sin tocar los resultados entregados")
    args = p.parse_args()

    if args.lista:
        print("Experimentos del informe:")
        for alias, (clave, desc, dura) in INFORME.items():
            print(f"  {alias:6} {desc}  [{dura}]")
        print("\nTodos los experimentos del script:")
        for clave, (desc, _) in EXPERIMENTOS.items():
            print(f"  {clave:6} {desc}")
        return

    # Las celdas que ya estan en el CSV se saltean (el script es reanudable).
    # Como el zip trae los resultados entregados, lo del informe (--todos y
    # exp1..exp4) mide SIEMPRE en otra carpeta: si no, no mediria nada.
    del_informe = args.todos or any(c in INFORME for c in args.experimento)
    if args.nuevo or del_informe:
        RESULTADOS = os.path.join(RAIZ, "experimentos", "resultados_nuevos")

    if not os.path.exists(BINARIO_CPP):
        raise SystemExit(f"No existe {BINARIO_CPP}. Corre 'make' desde TP1/ primero.")

    if args.completo:
        elegidos = list(EXPERIMENTOS)
    elif args.todos:
        elegidos = list(INFORME)
    else:
        elegidos = args.experimento
    if not elegidos:
        p.print_help()
        return
    elegidos = [INFORME[c][0] if c in INFORME else c for c in elegidos]

    print(f"Entorno guardado en {guardar_entorno()}")
    print(f"Resultados en {RESULTADOS}\n")
    for clave in elegidos:
        if clave not in EXPERIMENTOS:
            raise SystemExit(f"Experimento desconocido: {clave}. Usa --lista.")
        EXPERIMENTOS[clave][1](args)


if __name__ == "__main__":
    main()
