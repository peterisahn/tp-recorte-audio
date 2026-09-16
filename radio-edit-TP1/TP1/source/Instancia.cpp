#include "Instancia.h"
#include <cmath>
#include <fstream>
#include <stdexcept>
#include <string>

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

    if (!(archivo >> _n >> _d >> _k)) {
        throw runtime_error("Formato invalido: se esperaba 'n d k' en la primera linea de " + ruta);
    }

    // Hacen falta al menos dos pulsos porque el primero y el último se conservan siempre
    // , por lo mismo k >= 2, y no se pueden conservar más pulsos de los que existen
    if (_n < 2) {
        throw runtime_error("La instancia debe tener al menos 2 pulsos (n >= 2).");
    }
    if (_d < 1) {
        throw runtime_error("Cada pulso debe tener al menos una caracteristica (d >= 1).");
    }
    if (_k < 2 || _k > _n) {
        throw runtime_error("Debe cumplirse 2 <= k <= n.");
    }

    _features.clear();

    // Recorremos en un loop los n pulsos que vamos a ir llenando en _features
    // A su vez cada pulso vamos llenando con sus características que correspondan
    for (int i = 0; i < _n; i++) {
        vector<double> pulso;  // Inicialiamos el vector pulso vacío
        for (int m = 0; m < _d; m++) {
            double valor;
           
            if (!(archivo >> valor)) {
                throw runtime_error("Faltan caracteristicas en " + ruta + ": se esperaban " +
                                    to_string(_n * _d) + " valores.");
            }
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

    // Inicializamos una variable acumuladora
    double suma = 0.0;

    // Recorremos en un loop las características de ambos pulsos i,j
    for (int m = 0; m < _d ; m++) {
        // Hacemos la resta componente a componente
        double dif = _features[i][m] - _features[j-1][m];
        // Elevamos al cuadrado la diferencia
        dif = dif * dif;
        // Actualizamos la sumatoria
        suma += dif;
    }
    // Aplicamos raíz cuadrada sobre la sumatoria total
    suma = sqrt(suma);
    return suma;
}
