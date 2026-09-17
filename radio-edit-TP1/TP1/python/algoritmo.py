#!/usr/bin/env python3
"""Port a Python de source/Algoritmo.h.

Interfaz abstracta de la que heredan FuerzaBruta, Backtracking y
ProgramacionDinamica. Es el patron Strategy: main.py elige la implementacion en
crear_algoritmo() segun el flag --algoritmo y despues llama siempre a la misma
interfaz, igual que main.cpp. Eso es lo que hace que los tres compartan
exactamente el mismo camino de I/O y de cronometraje, que es lo que vuelve
comparables los tiempos.
"""

from abc import ABC, abstractmethod


class Algoritmo(ABC):
    @abstractmethod
    def resolver(self, instancia):
        ...

    @abstractmethod
    def nombre(self):
        ...
