CXX      = g++
CXXFLAGS = -std=c++17 -O2 -Wall -Wextra
SRCDIR   = source
OUTDIR   = output

SOURCES  = $(SRCDIR)/main.cpp \
           $(SRCDIR)/Instancia.cpp \
           $(SRCDIR)/Solucion.cpp \
           $(SRCDIR)/FuerzaBruta.cpp \
           $(SRCDIR)/Backtracking.cpp \
           $(SRCDIR)/ProgramacionDinamica.cpp

TARGET = radioedit

# ─── Targets principales ──────────────────────────────────────────────────────

all: $(TARGET)

$(TARGET): $(SOURCES)
	$(CXX) $(CXXFLAGS) -o $@ $^

# ─── Ejecución ────────────────────────────────────────────────────────────────

run-ejemplo: $(TARGET)
	./$(TARGET) --instancia input/ejemplo.txt --algoritmo pd

# ─── Experimentación ──────────────────────────────────────────────────────────

# Binario con contadores de nodos y de disparos de cada poda. Se compila de los
# MISMOS fuentes que radioedit -no hay una copia del algoritmo que se pueda
# desincronizar- y el binario que se entrega no lo compila: los contadores viven
# detrás de #ifdef INSTRUMENTAR y no cuestan nada si no se pide.
instrumentado: $(SOURCES)
	$(CXX) $(CXXFLAGS) -DINSTRUMENTAR -o radioedit_instr $^

# Variantes para el experimento de ablación: apagan una poda de backtracking
# cada vez, para medir cuánto aporta cada una por separado.
ablacion: $(SOURCES)
	$(CXX) $(CXXFLAGS) -DINSTRUMENTAR -DSIN_PODA_OPTIMALIDAD   -o radioedit_sin_opt  $^
	$(CXX) $(CXXFLAGS) -DINSTRUMENTAR -DSIN_PODA_FACTIBILIDAD  -o radioedit_sin_fact $^
	$(CXX) $(CXXFLAGS) -DINSTRUMENTAR -DSIN_PODA_OPTIMALIDAD -DSIN_PODA_FACTIBILIDAD -o radioedit_sin_podas $^

# ─── Tests ────────────────────────────────────────────────────────────────────

# Suite completa: humo, bordes, errores de parsing, coincidencia entre los tres
# algoritmos y contraste contra el oraculo. Si faltan las instancias las genera.
test: $(TARGET)
	python3 python/tests.py

# Sin fuerza bruta, que es la que tarda.
test-rapido: $(TARGET)
	python3 python/tests.py --rapido

# Regenera las instancias versionadas de input/instancias/.
instancias:
	python3 python/generador.py suite

# ─── Limpieza ─────────────────────────────────────────────────────────────────

clean:
	rm -f $(TARGET) radioedit_instr radioedit_sin_opt radioedit_sin_fact radioedit_sin_podas

clean-output:
	find $(OUTDIR) -type f ! -name '.gitkeep' -delete

# Windows (MinGW): usar `mingw32-make` en lugar de `make`.

.PHONY: all run-ejemplo instrumentado ablacion test test-rapido instancias clean clean-output
