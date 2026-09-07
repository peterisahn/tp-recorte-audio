#include "Instancia.h"
#include <cmath>
#include <fstream>
#include <stdexcept>

using namespace std;


Instancia::Instancia() : _n(0), _d(0), _k(0) {}

Instancia::Instancia(const std::string& ruta) : _n(0), _d(0), _k(0) {
    cargar(ruta);
}

void Instancia::cargar(const std::string& ruta) {

    ifstream archivo(ruta);

    if (!archivo.is_open()) {
        throw runtime_error("No se pudo abrir el archivo: " + ruta);
    }

    archivo >> _n >> _d >> _k;

    // Recorremos en un loop los n pulsos que vamos a ir llenando en _features
    // A su vez cada pulso vamos llenando con sus características que correspondan

    for (int i = 0; i < _n; i++) {
        vector<double> pulso;  // Inicialiamos el vector pulso vacío
        for (int m = 0; m < _d; m++) {
            double valor;
            archivo >> valor;
            pulso.push_back(valor); // Vamos agregando las características del pulso
        }
        _features.push_back(pulso); // Agregamos el vector pulso a _features
    }

}

int Instancia::n() const {
    return _n;
}

int Instancia::d() const {
    return _d;
}

int Instancia::k() const {
    return _k;
}

const std::vector<double>& Instancia::feature(int i) const {
    return _features[i];
}

double Instancia::costo(int i, int j) const {

    // Para obtener el costo de la diferencia entre ambos pulsos vamos a aplicar
    // la fórmula para calcular la distancia entre dos vectores.

    // Inicializamos una variable acumuladora 
    double suma = 0.0;

    // Recorremos en un loop las características de ambos pulsos i,j
    for (int m = 0; m < _d ; m++) {
        // Hacemos la resta componente a componente
        double dif = _features[i+1][m] - _features[j][m]; 
        // Elevamos al cuadrado la diferencia
        dif = dif * dif;
        // Actualizamos la sumatoria
        suma += dif;
    }
    // Aplicamos raíz cuadrada sobre la sumatoria total
    suma = sqrt(suma);
    return suma;
}


