#!/usr/bin/env python3
"""figura.py - genera las figuras del informe a partir de los CSV crudos.

    python3 python/figura.py --todas     # las figuras del informe
    python3 python/figura.py e1
    python3 python/figura.py e1 --limpio     # sin titulo ni epigrafe (para LaTeX)

Escribe SVG a mano: solo biblioteca estandar, como pide el requirements.txt de
la catedra. El SVG entra igual en LaTeX, en Google Docs y en Word, y al ser
vectorial no se pixela al imprimir.

Cada figura cumple lo que exige el instructivo (pag. 15): titulo, ejes
rotulados CON UNIDADES, leyenda, epigrafe, y escala consistente entre figuras
que se comparan.

La paleta esta validada para daltonismo (deuteranopia y tritanopia). Ademas cada
serie lleva un marcador y un trazo distintos, asi que la figura tambien se lee
impresa en blanco y negro.
"""

import argparse
import csv
import math
import os
import statistics

ACA = os.path.dirname(os.path.abspath(__file__))
TP1 = os.path.dirname(ACA)
RAIZ = os.path.dirname(TP1)
RESULTADOS = os.path.join(RAIZ, "experimentos", "resultados")
FIGURAS = os.path.join(RAIZ, "experimentos", "figuras")

# Paleta categorica validada (ver dataviz/references/palette.md).
# Cada serie: color, nombre, marcador y patron de trazo. El marcador y el trazo
# son la codificacion secundaria: sin ellos la figura impresa en gris se vuelve
# ilegible, y ademas el verde queda por debajo de 3:1 de contraste.
# La referencia no es un algoritmo medido sino un hecho combinatorio, asi que
# va en un gris neutro: no compite con las series y se lee como lo que es.
REFERENCIA = {"color": "#8a8a82", "nombre": "Recortes distintos que existen",
              "marca": "ninguno", "trazo": "5 4"}

# E4 compara FAMILIAS de instancia, no algoritmos, y las tres familias forman una
# escala ordenada: sin estructura -> estructura con ruido -> estructura perfecta.
# Para una variable ordenada corresponde una RAMPA de un solo tono, no colores
# categoricos. Se eligio el naranja, que es el color de backtracking en el resto
# de las figuras: las tres curvas son backtracking, y la rampa dice cuanta
# estructura tiene el material.
#
# Validada con dataviz/scripts/validate_palette.js: separacion para daltonismo
# dE 15,6 (protan) y 16,2 (tritan), vision normal 16,4, y las tres pasan 3:1 de
# contraste contra el fondo. El unico chequeo que no pasa es el de banda de
# luminosidad, que es categorico: una rampa TIENE que variar en luminosidad.
RAMPA_ESTRUCTURA = {
    "fam_aleatoria":   {"color": "#d97a35", "nombre": "Música aleatoria",
                        "marca": "circulo",   "trazo": ""},
    "fam_ruido":       {"color": "#a8420f", "nombre": "Repetitiva con ruido",
                        "marca": "cuadrado",  "trazo": "7 3"},
    "fam_repetitiva":  {"color": "#5c2208", "nombre": "Repetitiva exacta",
                        "marca": "triangulo", "trazo": "2 3"},
}

# Las dos podas son dos categorias DENTRO de backtracking, asi que se quedan en
# su tono. Validadas con dataviz/scripts/validate_palette.js: daltonismo dE 23,8
# y vision normal 27,0, las dos por encima de 3:1 de contraste.
PODAS = {
    "poda_fact": {"color": "#eb6834", "nombre": "Poda por factibilidad",
                  "marca": "cuadrado", "trazo": ""},
    "poda_opt":  {"color": "#7a2f10", "nombre": "Poda por optimalidad",
                  "marca": "circulo",  "trazo": ""},
}

# E6 parte las cuatro variantes de la ablacion en DOS pares segun este o no la
# poda por optimalidad, que es el hallazgo del experimento. El color codifica esa
# particion y reusa los dos tonos de PODAS -ya validados, dE 23,8 para daltonismo
# y 27,0 para vision normal-, asi que no hace falta validar una paleta nueva.
# Adentro de cada par la diferencia va por marcador y trazo, no por color.
ABLACION = {
    "abl_ninguna":   {"color": "#eb6834", "nombre": "Sin podas",
                      "marca": "ninguno",   "trazo": "2 3"},
    "abl_solo_fact": {"color": "#eb6834", "nombre": "Sólo poda por factibilidad",
                      "marca": "cuadrado",  "trazo": ""},
    "abl_solo_opt":  {"color": "#7a2f10", "nombre": "Sólo poda por optimalidad",
                      "marca": "triangulo", "trazo": "2 3"},
    "abl_ambas":     {"color": "#7a2f10", "nombre": "Las dos podas",
                      "marca": "circulo",   "trazo": ""},
}

# E8 parte las barras en dos categorias: la cantidad descartada cae justo en un
# limite de compas o no cae. Reusa los dos tonos ya validados de PODAS -dE 23,8
# para daltonismo y 27,0 para vision normal-, asi que no hay paleta nueva que
# validar. Aca el color ES el resultado: si los oscuros son sistematicamente mas
# bajos que los claros, el efecto existe.
COMPAS = {
    "en_compas": {"color": "#7a2f10", "nombre": "Cae justo en un compás",
                  "marca": "ninguno", "trazo": ""},
    "sin_compas": {"color": "#eb6834", "nombre": "No cae en un compás",
                   "marca": "ninguno", "trazo": ""},
}

# El costo del optimo no es de ningun algoritmo: es una propiedad de la
# grabacion. Por eso va en un gris azulado neutro, igual que la referencia
# combinatoria, y no en uno de los colores de FB/BT/PD.
COSTO = {"costo": {"color": "#4f5d6b", "nombre": "Costo del recorte óptimo",
                   "marca": "circulo", "trazo": ""}}

SERIES = {
    "ref": REFERENCIA,
    **COSTO,
    **PODAS,
    **ABLACION,
    **COMPAS,
    **RAMPA_ESTRUCTURA,
    "fb": {"color": "#2a78d6", "nombre": "Fuerza bruta",          "marca": "circulo",  "trazo": ""},
    "bt": {"color": "#eb6834", "nombre": "Backtracking",          "marca": "cuadrado", "trazo": "7 3"},
    "pd": {"color": "#1baf7a", "nombre": "Programación dinámica",  "marca": "triangulo","trazo": "2 3"},
}

TINTA = "#1a1a19"
TINTA2 = "#52514e"
GRILLA = "#e4e4e0"
EJE = "#b8b8b2"


def esc(t):
    return (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def fmt(x):
    """Formato con separador de miles a la espanola: 1.234,5"""
    if x >= 1000:
        return f"{x:,.0f}".replace(",", ".")
    if x >= 1:
        return f"{x:g}".replace(".", ",")
    return f"{x:g}".replace(".", ",")


class Lienzo:
    """Un grafico de lineas con ejes logaritmicos, emitido como SVG."""

    def __init__(self, ancho=780, alto=470, xlim=None, ylim=None,
                 logx=True, logy=True,
                 margen=(82, 150, 60, 78)):   # arriba, derecha, abajo, izquierda
        self.ancho, self.alto = ancho, alto
        self.logx, self.logy = logx, logy
        self.mt, self.mr, self.mb, self.ml = margen
        self.x0, self.x1 = xlim
        self.y0, self.y1 = ylim
        self.partes = []

    @property
    def ancho_util(self):
        return self.ancho - self.ml - self.mr

    @property
    def alto_util(self):
        return self.alto - self.mt - self.mb

    def px(self, v):
        if self.logx:
            f = (math.log10(v) - math.log10(self.x0)) / (math.log10(self.x1) - math.log10(self.x0))
        else:
            f = (v - self.x0) / (self.x1 - self.x0)
        return self.ml + f * self.ancho_util

    def py(self, v):
        if self.logy:
            f = (math.log10(self.y1) - math.log10(v)) / (math.log10(self.y1) - math.log10(self.y0))
        else:
            f = (self.y1 - v) / (self.y1 - self.y0)
        return self.mt + f * self.alto_util

    def add(self, s):
        self.partes.append(s)

    # ---- estructura ----

    def marco(self, xticks, yticks, xlabel, ylabel, xrotulos=None):
        # Grilla recesiva: guia la lectura sin competir con los datos.
        for v in yticks:
            y = self.py(v)
            self.add(f'<line x1="{self.ml}" y1="{y:.1f}" x2="{self.ml+self.ancho_util}" '
                     f'y2="{y:.1f}" stroke="{GRILLA}" stroke-width="1"/>')
            self.add(f'<text x="{self.ml-10}" y="{y+4:.1f}" text-anchor="end" font-size="11.5" '
                     f'fill="{TINTA2}" font-family="Helvetica,Arial,sans-serif">{esc(fmt(v))}</text>')
        for i, v in enumerate(xticks):
            x = self.px(v)
            self.add(f'<line x1="{x:.1f}" y1="{self.mt}" x2="{x:.1f}" '
                     f'y2="{self.mt+self.alto_util}" stroke="{GRILLA}" stroke-width="1"/>')
            self.add(f'<text x="{x:.1f}" y="{self.mt+self.alto_util+20}" text-anchor="middle" '
                     f'font-size="11.5" fill="{TINTA2}" font-family="Helvetica,Arial,sans-serif">'
                     f'{esc(xrotulos[i] if xrotulos else fmt(v))}</text>')
        # Ejes
        self.add(f'<line x1="{self.ml}" y1="{self.mt+self.alto_util}" x2="{self.ml+self.ancho_util}" '
                 f'y2="{self.mt+self.alto_util}" stroke="{EJE}" stroke-width="1.2"/>')
        self.add(f'<line x1="{self.ml}" y1="{self.mt}" x2="{self.ml}" '
                 f'y2="{self.mt+self.alto_util}" stroke="{EJE}" stroke-width="1.2"/>')
        # Rotulos CON UNIDADES (requisito del instructivo)
        # Si el panel comparte el eje X con el de abajo, xlabel viene vacio y no
        # se dibuja: repetir el mismo rotulo dos veces es ruido, y ademas choca
        # con el titulo del panel siguiente.
        if xlabel:
            self.add(f'<text x="{self.ml+self.ancho_util/2:.0f}" y="{self.mt+self.alto_util+46:.0f}" '
                     f'text-anchor="middle" font-size="12.5" fill="{TINTA}" '
                     f'font-family="Helvetica,Arial,sans-serif">{esc(xlabel)}</text>')
        # La etiqueta del eje Y se posiciona RELATIVA al panel, no en un x fijo:
        # con dos paneles en el mismo SVG un x fijo hace que se pisen entre si.
        yc = self.mt + self.alto_util / 2
        xe = max(14, self.ml - 62)
        self.add(f'<text x="{xe}" y="{yc:.0f}" text-anchor="middle" font-size="12.5" fill="{TINTA}" '
                 f'font-family="Helvetica,Arial,sans-serif" transform="rotate(-90 {xe} {yc:.0f})">{esc(ylabel)}</text>')

    def marcador(self, forma, x, y, color):
        if forma == "ninguno":
            return ""
        if forma == "circulo":
            return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.2" fill="{color}" stroke="#fcfcfb" stroke-width="1.6"/>'
        if forma == "cuadrado":
            return (f'<rect x="{x-4:.1f}" y="{y-4:.1f}" width="8" height="8" fill="{color}" '
                    f'stroke="#fcfcfb" stroke-width="1.6"/>')
        p = f"{x:.1f},{y-4.8:.1f} {x-4.6:.1f},{y+3.6:.1f} {x+4.6:.1f},{y+3.6:.1f}"
        return f'<polygon points="{p}" fill="{color}" stroke="#fcfcfb" stroke-width="1.6"/>'

    def serie(self, clave, puntos, etiqueta_final=None, grosor=None):
        cfg = SERIES[clave]
        dentro = [(x, y) for x, y in puntos if self.y0 <= y <= self.y1 and self.x0 <= x <= self.x1]
        if not dentro:
            return
        d = " ".join(f"{self.px(x):.1f},{self.py(y):.1f}" for x, y in dentro)
        dash = f' stroke-dasharray="{cfg["trazo"]}"' if cfg["trazo"] else ""
        if grosor is None:
            grosor = 1.5 if clave == "ref" else 2
        self.add(f'<polyline points="{d}" fill="none" stroke="{cfg["color"]}" stroke-width="{grosor}"'
                 f' stroke-linejoin="round" stroke-linecap="round"{dash}/>')
        for x, y in dentro:
            m = self.marcador(cfg["marca"], self.px(x), self.py(y), cfg["color"])
            if m:
                self.add(m)
        # Etiqueta directa al final de la linea. Va en tinta, no en el color de
        # la serie: el color lo aporta la linea que esta al lado.
        if etiqueta_final:
            ux, uy = dentro[-1]
            self.add(f'<text x="{self.px(ux)+12:.1f}" y="{self.py(uy)+4:.1f}" font-size="12" '
                     f'fill="{TINTA}" font-family="Helvetica,Arial,sans-serif" '
                     f'font-weight="600">{esc(etiqueta_final)}</text>')

    def anotacion(self, x, y, texto, dy=-16):
        self.add(f'<text x="{self.px(x):.1f}" y="{self.py(y)+dy:.1f}" text-anchor="middle" '
                 f'font-size="11" fill="{TINTA2}" font-style="italic" '
                 f'font-family="Helvetica,Arial,sans-serif">{esc(texto)}</text>')

    def leyenda(self, claves, y=None, nombres=None):
        """Leyenda HORIZONTAL, debajo del titulo. Asi no compite nunca con los
        datos, que es el problema tipico de meterla dentro del area del grafico.

        Si no entra a lo ancho, PASA A OTRO RENGLON. Sin esto la ultima serie se
        sale del lienzo y queda cortada: con 5 series pasa a 780 px de ancho."""
        y = self.mt - 30 if y is None else y
        x = self.ml
        for c in claves:
            ancho_entrada = 64 + len((nombres or {}).get(c, SERIES[c]["nombre"])) * 6.6
            if x > self.ml and x + ancho_entrada > self.ancho - self.mr:
                x, y = self.ml, y + 18
            cfg = SERIES[c]
            # Cada figura puede renombrar la serie: en una medimos tiempo y en
            # otra nodos, y la leyenda tiene que decir que es lo que se dibuja.
            etiqueta = (nombres or {}).get(c, cfg["nombre"])
            dash = f' stroke-dasharray="{cfg["trazo"]}"' if cfg["trazo"] else ""
            self.add(f'<line x1="{x}" y1="{y}" x2="{x+26}" y2="{y}" stroke="{cfg["color"]}" '
                     f'stroke-width="2"{dash}/>')
            m = self.marcador(cfg["marca"], x + 13, y, cfg["color"])
            if m:
                self.add(m)
            self.add(f'<text x="{x+34}" y="{y+4}" font-size="12" fill="{TINTA}" '
                     f'font-family="Helvetica,Arial,sans-serif">{esc(etiqueta)}</text>')
            x += 34 + len(etiqueta) * 6.6 + 30

    def nota(self, x, y, lineas, color=None):
        """Explicacion pegada a su curva. La primera linea nombra al algoritmo."""
        for i, linea in enumerate(lineas):
            if i == 0:
                self.add(f'<text x="{x}" y="{y}" font-size="12" font-weight="700" '
                         f'fill="{color or TINTA}" '
                         f'font-family="Helvetica,Arial,sans-serif">{esc(linea)}</text>')
            else:
                self.add(f'<text x="{x}" y="{y + i*16}" font-size="11.5" fill="{TINTA2}" '
                         f'font-family="Helvetica,Arial,sans-serif">{esc(linea)}</text>')


    def barras(self, grupos, claves, ancho_grupo=0.72, etiquetar=False, ancho_px=None):
        """Barras agrupadas. Solo tienen sentido con eje Y LINEAL y arrancando en
        cero: una barra codifica magnitud por su largo, y en escala logaritmica
        -o con el eje cortado- ese largo miente. Por eso este metodo exige y0=0.

        `grupos` es [(x, {clave: valor}), ...]."""
        if self.logy or self.y0 != 0:
            raise ValueError("barras() necesita eje Y lineal arrancando en 0")
        # Con ancho_px el grupo mide lo mismo siempre, aunque los x no esten
        # equiespaciados. Hace falta para que este panel comparta la escala X
        # con el de arriba y las dos mitades se puedan leer en vertical.
        if ancho_px is not None:
            paso = ancho_px / ancho_grupo
        elif len(grupos) < 2:
            paso = self.ancho_util
        else:
            paso = min(abs(self.px(b[0]) - self.px(a[0])) for a, b in zip(grupos, grupos[1:]))
        ancho = paso * ancho_grupo / len(claves)
        base = self.py(0)
        for x, valores in grupos:
            cx = self.px(x)
            izq = cx - paso * ancho_grupo / 2
            for i, clave in enumerate(claves):
                v = valores.get(clave, 0)
                bx = izq + i * ancho
                by = self.py(v)
                alto = base - by
                # Separacion de 2 px entre barras vecinas: sin ese respiro dos
                # barras contiguas se leen como una sola.
                if alto >= 0.5:
                    self.add(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{max(1, ancho-2):.1f}" '
                             f'height="{alto:.1f}" fill="{SERIES[clave]["color"]}" rx="2"/>')
                if etiquetar:
                    self.add(f'<text x="{bx + (ancho-2)/2:.1f}" y="{by-5:.1f}" '
                             f'text-anchor="middle" font-size="9.5" fill="{TINTA2}" '
                             f'font-family="Helvetica,Arial,sans-serif">{esc(fmt(v))}</text>')

    def titulo_panel(self, letra, texto, dy=38):
        """Rotulo (a)/(b) de un panel, arriba a la izquierda de su area.

        `dy` es cuanto por encima del area de datos va. Se sube cuando la
        leyenda ocupa dos renglones y si no se le encimaria."""
        self.add(f'<text x="{self.ml}" y="{self.mt-dy}" font-size="12.5" font-weight="700" '
                 f'fill="{TINTA}" font-family="Helvetica,Arial,sans-serif">'
                 f'({esc(letra)}) {esc(texto)}</text>')

    def render(self, titulo=None):
        """El epigrafe NO va dentro de la imagen: va en el documento, con el
        mecanismo de figuras del procesador de texto (\\caption en LaTeX). Se
        escribe aparte, en un .txt al lado del SVG."""
        cab = []
        if titulo:
            cab.append(f'<text x="{self.ml}" y="28" font-size="15.5" font-weight="700" fill="{TINTA}" '
                       f'font-family="Helvetica,Arial,sans-serif">{esc(titulo)}</text>')
        return ('<?xml version="1.0" encoding="UTF-8"?>\n'
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.ancho}" height="{self.alto}" '
                f'viewBox="0 0 {self.ancho} {self.alto}" font-family="Helvetica,Arial,sans-serif">\n'
                f'<rect width="{self.ancho}" height="{self.alto}" fill="#fcfcfb"/>\n'
                + "\n".join(cab + self.partes) + "\n</svg>\n")



def componer(lienzos, ancho, alto, titulo=None):
    """Junta varios Lienzos en un solo SVG (small multiples, como la Fig. 4 del
    instructivo de la catedra). Cada panel ya trae sus margenes calculados para
    ocupar su region del lienzo grande, asi que aca solo se concatenan."""
    cab = []
    if titulo:
        cab.append(f'<text x="{lienzos[0].ml}" y="26" font-size="15.5" font-weight="700" '
                   f'fill="{TINTA}" font-family="Helvetica,Arial,sans-serif">{esc(titulo)}</text>')
    partes = [p for g in lienzos for p in g.partes]
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{ancho}" height="{alto}" '
            f'viewBox="0 0 {ancho} {alto}" font-family="Helvetica,Arial,sans-serif">\n'
            f'<rect width="{ancho}" height="{alto}" fill="#fcfcfb"/>\n'
            + "\n".join(cab + partes) + "\n</svg>\n")


def envolver(texto, ancho):
    palabras, lineas, actual = texto.split(), [], ""
    for p in palabras:
        if len(actual) + len(p) + 1 > ancho:
            lineas.append(actual); actual = p
        else:
            actual = (actual + " " + p).strip()
    if actual:
        lineas.append(actual)
    return lineas


# ---------------------------------------------------------------------------
# Lectura de resultados
# ---------------------------------------------------------------------------

def medianas(experimento, campo_x="n", campo_v="ms", filtro=None):
    """Lee el CSV crudo y devuelve {algoritmo: [(x, mediana), ...]}."""
    ruta = os.path.join(RESULTADOS, f"{experimento}.csv")
    if not os.path.exists(ruta):
        raise SystemExit(f"No existe {ruta}. Corre primero: python3 python/experimentos.py")
    bolsa = {}
    with open(ruta, newline="") as f:
        for fila in csv.DictReader(f):
            if filtro and not filtro(fila):
                continue
            clave = (fila["algoritmo"], float(fila[campo_x]))
            bolsa.setdefault(clave, []).append(float(fila[campo_v]))
    salida = {}
    for (alg, x), valores in bolsa.items():
        salida.setdefault(alg, []).append((x, statistics.median(valores)))
    for alg in salida:
        salida[alg].sort()
    return salida


# ---------------------------------------------------------------------------
# E1
# ---------------------------------------------------------------------------

def figura_e1(limpio=False):
    datos = medianas("e1_escalabilidad_n")
    g = Lienzo(xlim=(9, 2600), ylim=(0.0012, 20000))
    g.marco(xticks=[10, 20, 50, 100, 200, 500, 1000, 2000],
            yticks=[0.002, 0.01, 0.1, 1, 10, 100, 1000, 10000],
            xlabel="Cantidad de pulsos de la grabación   (escala logarítmica)",
            ylabel="Tiempo en resolver [ms]   (escala logarítmica)")
    g.leyenda(["fb", "bt", "pd"])

    for clave in ("pd", "bt", "fb"):
        if clave in datos:
            g.serie(clave, datos[clave])

    # NADA de texto explicativo dentro de la imagen: el grafico queda limpio y
    # el analisis va en el cuerpo del informe, donde se puede editar sin
    # regenerar la figura. El texto se escribe aparte, en e1_analisis.md.

    titulo = None if limpio else "Hasta dónde llega cada algoritmo"
    return g.render(titulo)


def figura_e2(limpio=False):
    """E2 - dos paneles (small multiples, como la Fig. 4 del instructivo).

    (a) LINEAS, porque lo que se lee es la FORMA de la curva contra la
        referencia combinatoria, sobre 7 ordenes de magnitud: eso pide log.
    (b) BARRAS, porque son conteos por categoria y lo que se compara es
        "cual de las dos podas manda en cada zona". Una barra codifica magnitud
        por su largo, asi que va en eje lineal arrancando en cero.

    Las dos mitades responden preguntas distintas y por eso van juntas en vez de
    repetir la misma informacion dos veces.
    """
    import math as _m
    N = 24
    # Paneles APILADOS, no lado a lado: mantiene el ancho de 780 del resto de las
    # figuras (el instructivo pide escala consistente entre figuras que se
    # comparan) y le deja a cada leyenda el ancho completo.
    ANCHO, ALTO, ML = 780, 700, 100

    # --- panel (a): nodos contra la cantidad de recortes que existen ---
    a = Lienzo(ancho=ANCHO, alto=ALTO, xlim=(2, 24), ylim=(0.7, 3e7),
               logx=False, margen=(88, 40, ALTO - 88 - 230, ML))
    a.marco(xticks=[2, 4, 8, 12, 16, 20, 24],
            yticks=[1, 100, 10000, 1000000, 10000000],
            xlabel="",   # eje X compartido con el panel (b), rotulado alla abajo
            ylabel="Cantidad   (escala log.)")
    a.titulo_panel("a", "Cuánto recorre cada algoritmo")
    a.leyenda(["ref", "fb", "bt"], y=a.mt - 18,
              nombres={"ref": "Recortes que existen", "fb": "Nodos de fuerza bruta",
                       "bt": "Nodos de backtracking"})
    a.serie("ref", [(k, max(1, _m.comb(N - 2, k - 2))) for k in range(2, N + 1)])
    datos = medianas("e2_barrido_k", campo_x="k", campo_v="nodos",
                     filtro=lambda f: f["nodos"] != "")
    for clave in ("fb", "bt"):
        if clave in datos:
            a.serie(clave, [(x, max(1, y)) for x, y in datos[clave]])

    # --- panel (b): cuantas veces dispara cada poda ---
    podas = {}
    for campo in ("poda_fact", "poda_opt"):
        d = medianas("e2_barrido_k", campo_x="k", campo_v=campo,
                     filtro=lambda f, c=campo: f["algoritmo"] == "bt" and f[c] != "")
        podas[campo] = dict(d.get("bt", []))

    # Las barras van en el MISMO eje X que el panel (a), en la posicion real de
    # cada k, y con ancho fijo en pixeles. Asi las dos mitades se leen en
    # vertical: el pico de la poda por optimalidad cae justo donde el panel de
    # arriba muestra la zona media.
    ks = [4, 8, 10, 12, 16, 18, 20, 22, 24]
    b = Lienzo(ancho=ANCHO, alto=ALTO, xlim=(2, 24), ylim=(0, 700),
               logx=False, logy=False, margen=(432, 40, ALTO - 432 - 213, ML))
    b.marco(xticks=[2, 4, 8, 12, 16, 20, 24], yticks=[0, 200, 400, 600],
            xlabel="Pulsos que se conservan  k",
            ylabel="Veces que dispara")
    b.titulo_panel("b", "Cuál de las dos podas hace el trabajo")
    b.leyenda(["poda_fact", "poda_opt"], y=b.mt - 18,
              nombres={"poda_fact": "Poda por factibilidad",
                       "poda_opt": "Poda por optimalidad"})
    b.barras([(k, {"poda_fact": podas["poda_fact"].get(k, 0),
                   "poda_opt": podas["poda_opt"].get(k, 0)}) for k in ks],
             ["poda_fact", "poda_opt"], etiquetar=True, ancho_px=30)

    titulo = None if limpio else "Cuánto trabaja cada algoritmo según cuánto se recorta"
    return componer([a, b], ANCHO, ALTO, titulo)


def figura_e3(limpio=False):
    """E3 - cuanto pesa d.

    El eje vertical esta NORMALIZADO: cada curva se divide por su propio tiempo
    con d=1. Es la unica forma de poner en el mismo grafico a FB (que se mide en
    n=20) y a PD (que se mide en n=600, porque en n=20 tarda 0,005 ms y el
    efecto se pierde en el ruido). Lo que se compara no son tiempos sino FORMAS.

    La linea gris es la referencia: donde estaria la curva si el tiempo fuera
    proporcional a d, que es lo que dice la complejidad teorica. La distancia
    entre las mediciones y esa linea es el resultado del experimento.

    BT no va en la figura a proposito: su tiempo en n=20 es de 0,04 a 0,24 ms, y
    entre instancias con el mismo d le varia mas que entre d distintos. Ponerlo
    aca invitaria a leer como efecto de d lo que es sorteo de la instancia. Sus
    nodos van en una tabla en el texto, con mediana y rango.
    """
    def curva(alg, n):
        datos = medianas("e3_barrido_d", campo_x="d",
                         filtro=lambda f, a=alg, nn=n: f["algoritmo"] == a and int(f["n"]) == nn)
        puntos = datos.get(alg, [])
        if not puntos:
            return []
        base = puntos[0][1]
        return [(d, t / base) for d, t in puntos]

    # Margen derecho chico: esta figura no lleva etiquetas al final de las
    # lineas, asi que el area de datos puede ocupar todo el ancho.
    g = Lienzo(xlim=(1, 105), ylim=(0.85, 130), margen=(82, 40, 60, 78))
    g.marco(xticks=[1, 2, 4, 8, 16, 32, 64, 96],
            yticks=[1, 2, 5, 10, 20, 50, 100],
            xlabel="Características por pulso  d   (escala logarítmica)",
            ylabel="Veces más lento que con d = 1   (escala logarítmica)")
    g.leyenda(["ref", "fb", "pd"], nombres={
        "ref": "Crecimiento proporcional a d",
        "fb": "Fuerza bruta (n=20)",
        "pd": "Prog. dinámica (n=600)",
    })

    # Referencia teorica: si el tiempo fuera proporcional a d, duplicar d
    # duplicaria el tiempo y la curva seria exactamente esta.
    g.serie("ref", [(d, float(d)) for d in (1, 2, 4, 8, 16, 32, 64, 96)])
    g.serie("fb", curva("fb", 20))
    g.serie("pd", curva("pd", 600))

    titulo = None if limpio else "Cuánto cuesta agregarle características a cada pulso"
    return g.render(titulo)





def figura_e4k(limpio=False):
    """E4k - por que el colapso de backtracking depende de k.

    Dos paneles APILADOS que comparten el eje X, para que la relacion se lea en
    vertical: donde el costo del optimo toca cero, los nodos se desploman.

    (a) BARRAS: el costo es una magnitud con cero significativo, y lo que
        importa es justamente si vale cero o no. Una barra de altura cero lo
        dice de un vistazo.
    (b) LINEA en log: los nodos se mueven entre 77 y 1,2 millones, cuatro
        ordenes de magnitud que ninguna barra puede mostrar honestamente.
    """
    ANCHO, ALTO, ML = 780, 660, 100
    N = 120
    costo = dict(medianas("e4k_colapso_segun_k", campo_x="k", campo_v="costo",
                          filtro=lambda f: f["algoritmo"] == "pd").get("pd", []))
    nodos = dict(medianas("e4k_colapso_segun_k", campo_x="k", campo_v="nodos",
                          filtro=lambda f: f["algoritmo"] == "bt" and f["nodos"] != "").get("bt", []))
    ks = sorted(costo)

    a = Lienzo(ancho=ANCHO, alto=ALTO, xlim=(25, 125), ylim=(0, 1.0),
               logx=False, logy=False, margen=(86, 40, ALTO - 86 - 190, ML))
    a.marco(xticks=[30, 40, 48, 60, 72, 80, 90, 100, 120], yticks=[0, 0.25, 0.5, 0.75, 1.0],
            xlabel="", ylabel="Costo del óptimo")
    a.titulo_panel("a", "¿Existe un recorte que no cueste nada?")
    a.barras([(k, {"costo": costo[k]}) for k in ks], ["costo"], ancho_px=26)
    # Las barras de altura cero son el resultado: se rotulan para que no se lean
    # como un dato faltante.
    for k in ks:
        if costo[k] == 0:
            a.add(f'<text x="{a.px(k):.1f}" y="{a.py(0)-7:.1f}" text-anchor="middle" '
                  f'font-size="10.5" font-weight="700" fill="#1baf7a" '
                  f'font-family="Helvetica,Arial,sans-serif">0</text>')

    b = Lienzo(ancho=ANCHO, alto=ALTO, xlim=(25, 125), ylim=(40, 3e6),
               logx=False, margen=(400, 40, ALTO - 400 - 200, ML))
    b.marco(xticks=[30, 40, 48, 60, 72, 80, 90, 100, 120],
            yticks=[100, 1000, 10000, 100000, 1000000],
            xlabel="Pulsos que se conservan  k   (de una grabación de 120)",
            ylabel="Nodos de BT   (escala log.)")
    b.titulo_panel("b", "Cuánto tiene que buscar backtracking")
    b.serie("bt", [(k, nodos[k]) for k in ks if k in nodos])

    titulo = None if limpio else "Por qué no alcanza con que la música se repita"
    return componer([a, b], ANCHO, ALTO, titulo)


def celdas_completas(experimento, algoritmo, semillas):
    """Devuelve las celdas (familia, n) que tienen TODAS las semillas medidas.

    Hace falta porque el driver corta una celda apenas una instancia se pasa del
    limite de tiempo, y deja escritas las corridas de las instancias anteriores.
    Promediar eso reporta solo las instancias faciles."""
    ruta = os.path.join(RESULTADOS, f"{experimento}.csv")
    vistas = {}
    with open(ruta, newline="") as f:
        for fila in csv.DictReader(f):
            if fila["algoritmo"] != algoritmo:
                continue
            vistas.setdefault((fila["familia"], int(fila["n"])), set()).add(fila["semilla"])
    return {c for c, s in vistas.items() if len(s) >= semillas}


def figura_e4(limpio=False):
    """E4 - cuanto cambia que la musica sea repetitiva.

    Las tres curvas son BACKTRACKING sobre tres familias de instancia. La linea
    gris no es una medicion: es la recta n-3. Si la curva del material
    repetitivo cae justo encima, la linealidad queda probada a la vista.
    """
    FAM = {"fam_aleatoria": "aleatoria",
           "fam_ruido": "estructurada_r0.02",
           "fam_repetitiva": "estructurada"}

    # Solo se grafican las celdas con las 5 instancias completas. En el borde
    # donde un algoritmo se esta muriendo pasa que las instancias faciles
    # terminan dentro del limite de 10 s y las dificiles no: la mediana de las
    # que sobreviven queda sesgada HACIA ABAJO y dibujaria una curva mas
    # optimista que la realidad. Concretamente, con ruido y n=1800 terminan 2 de
    # 5, asi que ese punto no va.
    completas = celdas_completas("e4_estructura", "bt", semillas=5)

    def curva(clave):
        fa = FAM[clave]
        datos = medianas("e4_estructura", campo_x="n", campo_v="nodos",
                         filtro=lambda f: (f["algoritmo"] == "bt"
                                           and f["familia"] == fa
                                           and f["nodos"] != ""
                                           and (fa, int(f["n"])) in completas))
        return [(x, max(1, y)) for x, y in datos.get("bt", [])]

    # Margen izquierdo grande: el eje llega a 10.000.000 y esos rotulos son largos.
    g = Lienzo(xlim=(11, 3000), ylim=(8, 3e7), margen=(82, 40, 60, 100))
    g.marco(xticks=[12, 24, 60, 120, 300, 600, 1200, 2400],
            yticks=[10, 100, 1000, 10000, 100000, 1000000, 10000000],
            xlabel="Cantidad de pulsos de la grabación   (escala logarítmica)",
            ylabel="Nodos que visita backtracking   (escala logarítmica)")
    g.leyenda(["ref", "fam_aleatoria", "fam_ruido", "fam_repetitiva"],
              nombres={"ref": "Lineal (n − 3)", "fam_aleatoria": "Aleatoria",
                       "fam_ruido": "Repetitiva + ruido",
                       "fam_repetitiva": "Repetitiva exacta"})

    # La referencia va GRUESA y debajo de todo: la curva del material repetitivo
    # cae exactamente encima, y con un trazo fino quedaria tapada justo la linea
    # que sirve para probar que es lineal. Asi se ve apoyada sobre la gris.
    g.serie("ref", [(n, n - 3) for n in (12, 24, 60, 120, 300, 600, 1200, 2400)],
            grosor=6)
    for clave in ("fam_aleatoria", "fam_ruido", "fam_repetitiva"):
        g.serie(clave, curva(clave))

    titulo = None if limpio else "Cuánto le cambia a backtracking que la música se repita"
    return g.render(titulo)


def figura_e6(limpio=False):
    """E6 - ablacion: dos paneles con EXACTAMENTE los mismos ejes.

    Se eligieron lineas y no barras porque lo que se lee es la FORMA: dos de las
    cuatro curvas crecen exponencialmente y dos se quedan casi planas, sobre seis
    ordenes de magnitud. Eso pide log, y en log una barra miente.

    CODIFICACION. Las cuatro variantes no son cuatro categorias sueltas: se
    parten en dos pares segun este o no la poda por OPTIMALIDAD, que es el
    hallazgo. Por eso el color codifica esa particion -los dos tonos ya
    validados de PODAS- y adentro de cada par la diferencia (la poda por
    factibilidad) va por marcador y trazo. La figura dice asi, sin leerse el
    texto, que el color es lo que importa y el trazo es el detalle.

    La linea gris gruesa es fuerza bruta, y la curva "sin podas" cae exactamente
    encima: esa superposicion es la comprobacion de que los dos algoritmos
    recorren el mismo arbol.
    """
    VARIANTES = [("abl_ninguna",   "cpp_sin_podas"),
                 ("abl_solo_fact", "cpp_sin_opt"),
                 ("abl_solo_opt",  "cpp_sin_fact"),
                 ("abl_ambas",     "cpp_ambas")]
    # Los dos paneles tienen la MISMA altura de area de datos (210 px) y los
    # mismos limites: si no, comparar una curva de arriba con una de abajo
    # enganaria, que es justo lo que un small multiple tiene que evitar.
    ANCHO, ALTO, ML, H = 780, 710, 100, 210
    XTICKS = [10, 12, 16, 20, 24, 30, 36]
    YTICKS = [10, 100, 1000, 10000, 100000, 1000000, 10000000]

    def curva(impl, familia, algoritmo="bt"):
        datos = medianas("e6_ablacion_podas", campo_x="n", campo_v="nodos",
                         filtro=lambda f: (f["algoritmo"] == algoritmo
                                           and f["implementacion"] == impl
                                           and f["familia"] == familia
                                           and f["nodos"] != ""))
        return [(x, max(1, y)) for x, y in datos.get(algoritmo, [])]

    def panel(margen, familia, letra, texto, con_leyenda, xlabel):
        # Con leyenda de dos renglones el titulo del panel sube, para que la
        # segunda fila de la leyenda no le caiga encima.
        g = Lienzo(ancho=ANCHO, alto=ALTO, xlim=(9, 37), ylim=(5, 1.4e7),
                   logx=False, margen=margen)
        g.marco(xticks=XTICKS, yticks=YTICKS, xlabel=xlabel,
                ylabel="Nodos   (escala log.)")
        g.titulo_panel(letra, texto, dy=74 if con_leyenda else 38)
        if con_leyenda:
            g.leyenda(["ref"] + [c for c, _ in VARIANTES], y=g.mt - 52,
                      nombres={"ref": "Fuerza bruta", "abl_ninguna": "Sin podas",
                               "abl_solo_fact": "Sólo factibilidad",
                               "abl_solo_opt": "Sólo optimalidad",
                               "abl_ambas": "Las dos"})
        # Fuerza bruta debajo de todo y gruesa: "sin podas" se le apoya encima.
        g.serie("ref", curva("cpp", familia, algoritmo="fb"), grosor=6)
        for clave, impl in VARIANTES:
            g.serie(clave, curva(impl, familia))
        return g

    # Margen superior mas alto que los demas paneles: aca la leyenda tiene
    # cinco series y ocupa dos renglones.
    a = panel((136, 40, ALTO - 136 - H, ML), "aleatoria", "a",
              "Música aleatoria: el caso adverso", True, "")
    b = panel((442, 40, ALTO - 442 - H, ML), "estructurada", "b",
              "Música perfectamente repetitiva", False,
              "Cantidad de pulsos de la grabación  n      (k = n/2, d = 12)")

    titulo = None if limpio else "Qué aporta cada poda de backtracking"
    return componer([a, b], ANCHO, ALTO, titulo)


def figura_e7(limpio=False):
    """E7 - cuantas veces mas lento es Python que C++, segun el algoritmo.

    UNICA figura del informe con el eje vertical LINEAL, y es a proposito. Lo
    que se dibuja es una RAZON entre dos tiempos, no un tiempo: va de 17 a 207,
    o sea poco mas de un orden de magnitud, y en lineal se lee directo "cuantas
    veces". En logaritmica las tres curvas se aplastarian y se perderia
    justamente lo que importa, que es cuanto se separan entre si.

    Los tiempos absolutos NO se grafican: son los mismos de E1 y estarian
    repetidos. Van en la tabla, que es lo que la figura no muestra.
    """
    def razon(alg):
        pares = {}
        for impl in ("cpp", "py"):
            d = medianas("e7_cpp_vs_python", campo_x="n", campo_v="ms",
                         filtro=lambda f, i=impl: (f["algoritmo"] == alg
                                                   and f["implementacion"] == i))
            pares[impl] = dict(d.get(alg, []))
        comunes = sorted(set(pares["cpp"]) & set(pares["py"]))
        return [(n, pares["py"][n] / pares["cpp"][n]) for n in comunes]

    g = Lienzo(xlim=(9, 330), ylim=(0, 230), logy=False, margen=(82, 150, 60, 88))
    g.marco(xticks=[10, 20, 40, 60, 100, 200, 300],
            yticks=[0, 50, 100, 150, 200],
            xlabel="Cantidad de pulsos de la grabación  n      (escala logarítmica)",
            ylabel="Veces más lento que C++")
    g.leyenda(["fb", "bt", "pd"])
    for alg in ("fb", "bt", "pd"):
        puntos = razon(alg)
        if puntos:
            g.serie(alg, puntos, etiqueta_final=f"{puntos[-1][1]:,.0f}×")

    # Las tres curvas mueren en n distintos y la figura no lo dice sola: sin
    # esta nota se leeria que fuerza bruta "se queda" en 29x, cuando en realidad
    # deja de poder medirse.
    g.nota(g.px(11), g.py(205), [
        "Cada curva termina donde la versión de",
        "Python pasa los 10 s y deja de medirse.",
    ])

    titulo = None if limpio else "Cuánto se paga por escribir el mismo algoritmo en Python"
    return g.render(titulo)


def figura_e8(limpio=False):
    """E8 - el costo del recorte optimo es un peine, no una curva.

    BARRAS Y NO LINEAS. El dato es un valor por cada cantidad ENTERA de pulsos
    descartados: no hay nada entre 7 y 8. Una linea insinuaria una continuidad
    que no existe, y con 48 puntos oscilantes ademas se vuelve ilegible. En
    barras cada valor se lee solo y los valles caen a la vista.

    UN PANEL POR GRABACION. Con las dos series encimadas en un mismo panel la
    figura era ilegible. Apiladas, cada peine se lee entero y la comparacion la
    hace el ojo entre paneles, que es para lo que existen los small multiples.

    NORMALIZADA. Cada panel se divide por la mediana de su propia grabacion: los
    costos absolutos van de 0,04 a 0,19 y sin normalizar los dos paneles no
    compartirian escala. Asi el 1,0 significa "el costo tipico de esta
    grabacion" y las dos se leen sobre la misma regla.

    Las marcas del eje caen cada 4 pulsos, o sea en los limites de compas. Que
    los valles del panel (a) caigan justo en las marcas es el resultado.
    """
    # ALTO da lugar al rotulo del eje X del panel de abajo, que con 620 se cortaba.
    ANCHO, ALTO, ML, H = 780, 664, 92, 200
    E8_COMPAS = 4          # pulsos por compas en 4/4, igual que en experimentos.py
    XTICKS = list(range(4, 49, 4))
    RUTAS = {"cancion": "propias/cancion", "fishin": "librosa/fishin"}

    def barras_de(grabacion):
        """[(pulsos descartados, costo / mediana)] para esa grabacion."""
        datos = medianas("e8_cuanto_recortar", campo_x="k", campo_v="costo",
                         filtro=lambda f: (f["algoritmo"] == "pd"
                                           and f["familia"] == "audio:" + grabacion))
        puntos = datos.get("pd", [])
        if not puntos:
            return []
        with open(os.path.join(TP1, "input", RUTAS[grabacion] + ".txt")) as fh:
            n = int(fh.readline().split()[0])
        pares = sorted((n - k, c) for k, c in puntos)
        mediana = statistics.median(c for _, c in pares)
        return [(dd, c / mediana) for dd, c in pares if 0 < dd <= 48]

    def panel(margen, grabacion, letra, texto, xlabel, con_leyenda=False):
        g = Lienzo(ancho=ANCHO, alto=ALTO, xlim=(0, 49), ylim=(0, 2.2),
                   logx=False, logy=False, margen=margen)
        g.marco(xticks=XTICKS, yticks=[0, 0.5, 1.0, 1.5, 2.0],
                xlabel=xlabel, ylabel="Costo ÷ costo típico",
                xrotulos=[str(x) if (x // 4) % 2 == 1 else "" for x in XTICKS])
        g.titulo_panel(letra, texto, dy=54 if con_leyenda else 38)
        if con_leyenda:
            g.leyenda(["en_compas", "sin_compas"], y=g.mt - 34)
        # Dos pasadas, una por categoria. Con una sola clave la barra queda
        # centrada en su x, asi que las dos pasadas no se pisan ni se corren.
        datos = barras_de(grabacion)
        for clave, cae in (("sin_compas", False), ("en_compas", True)):
            g.barras([(dd, {clave: v}) for dd, v in datos
                      if (dd % E8_COMPAS == 0) == cae],
                     [clave], ancho_px=11)
        return g

    a = panel((104, 40, ALTO - 104 - H, ML), "cancion", "a",
              "Reggaetón hecho con secuenciador", "", con_leyenda=True)
    b = panel((400, 40, ALTO - 400 - H, ML), "fishin", "b",
              "Folk tocado por una persona",
              "Pulsos que se descartan      (un compás son 4 pulsos)")

    titulo = None if limpio else "Lo que decide el costo no es cuánto se recorta, sino dónde cae el corte"
    return componer([a, b], ANCHO, ALTO, titulo)


FIGURAS_DISPONIBLES = {"e1": ("Escalabilidad en n", figura_e1),
                       "e2": ("Barrido de k", figura_e2),
                       "e3": ("Barrido de d", figura_e3),
                       "e4": ("Estructura de los datos", figura_e4),
                       "e4k": ("Control de E4: el colapso segun k", figura_e4k),
                       "e6": ("Ablacion de podas", figura_e6),
                       "e7": ("C++ contra Python", figura_e7),
                       "e8": ("Cuanto cuesta recortar", figura_e8)}


# Las figuras que aparecen en el informe, y el CSV del que sale cada una.
FIGURAS_INFORME = {"e1": "e1_escalabilidad_n", "e7": "e7_cpp_vs_python"}

NUEVOS = os.path.join(RAIZ, "experimentos", "resultados_nuevos")


def main():
    global RESULTADOS, FIGURAS
    p = argparse.ArgumentParser(description="Genera las figuras del informe.")
    p.add_argument("figura", nargs="*")
    p.add_argument("--todas", action="store_true", help="las figuras del informe")
    p.add_argument("--completo", action="store_true", help="todas las figuras del script")
    p.add_argument("--limpio", action="store_true", help="sin titulo ni epigrafe, para LaTeX")
    args = p.parse_args()

    if args.completo:
        elegidas = list(FIGURAS_DISPONIBLES)
    elif args.todas:
        elegidas = list(FIGURAS_INFORME)
    else:
        elegidas = args.figura
    if not elegidas:
        p.print_help()
        return

    entregados, figuras_entregadas = RESULTADOS, FIGURAS
    for clave in elegidas:
        if clave not in FIGURAS_DISPONIBLES:
            raise SystemExit(f"Figura desconocida: {clave}")
        nombre, fn = FIGURAS_DISPONIBLES[clave]
        # Si experimentos.py midio desde cero (resultados_nuevos/), se dibuja con
        # esas mediciones y en otra carpeta, para no pisar las figuras entregadas.
        csv_nuevo = os.path.join(NUEVOS, FIGURAS_INFORME.get(clave, "") + ".csv")
        if clave in FIGURAS_INFORME and os.path.exists(csv_nuevo):
            RESULTADOS = NUEVOS
            FIGURAS = os.path.join(RAIZ, "experimentos", "figuras_nuevas")
        else:
            RESULTADOS, FIGURAS = entregados, figuras_entregadas
        os.makedirs(FIGURAS, exist_ok=True)
        svg = fn(limpio=args.limpio)
        ruta = os.path.join(FIGURAS, f"{clave}.svg")
        with open(ruta, "w") as f:
            f.write(svg)
        print(f"  {clave}: {nombre}   (datos de {os.path.relpath(RESULTADOS, RAIZ)})")
        print(f"     -> {os.path.relpath(ruta, RAIZ)}")
        # El epigrafe y el analisis NO se generan: son prosa que se edita a
        # mano y vive en experimentos/textos/.


if __name__ == "__main__":
    main()
