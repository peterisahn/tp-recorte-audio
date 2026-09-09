#include "Solucion.h"
#include "Instancia.h"
#include <iostream>
#include <fstream>
#include <vector>
using namespace std;

Solucion::Solucion() {}

void Solucion::agregar(int pulso) {
    // Agregamos el índice del pulso al final de  _indices
    _indices.push_back(pulso);
}

void Solucion::limpiar() {
    // Borramos todo el vector _indices
    _indices.clear();
}

const std::vector<int>& Solucion::indices() const {
    // Devolvemos  _indices, que contiene los indices con la solución óptima para el recorte
    return _indices;
}

int Solucion::cantidad() const {
    // Devolvemos el tamaño de _indices, que debería coincidir con k
    return _indices.size();
}

double Solucion::costo(const Instancia& instancia) const {

    // Inicializamos el costo_total en 0.0
    double costo_total = 0.0;

    // Recorremos el vector _indices y vamos sumando los costos entre dos pulsos adyacentes usando sus índices
    int i = 0;
    while (i<_indices.size()-1){
        // Usamos el vector _indices para saber la posición del iésimo pulso y el iésimo+1 de la instancia original
        costo_total += instancia.costo(_indices[i], _indices[i+1]);
        i+=1;
    }
    // Devolvemos el costo_total de la solución
    return costo_total;
}

bool Solucion::esValida(const Instancia& instancia) const {
    // Para que sea considerado una solución válida debe cumplir:
    // - El tamaño de la solución debe ser exactamente k
    // - El primer pulso y el último deben mantenerse
    // - Los índices en _indices deben estar ordenados

    // Tiene tamaño k la solución
    if (cantidad() != instancia.k()) {
        return false;
    }

    // El primer índice siempre es 1
    if (_indices[0] != 1) {
        return false;
    }

    // El último pulso de la instancia original debe mantenerse
    if (_indices[cantidad() - 1] != instancia.n()) {
        return false;
    }
    for (int i = 0; i < cantidad() - 1; i++) {
        if (_indices[i] >= _indices[i + 1]) {
            return false;
        }
    }

    // Si cumple todas estas condiciones, devuelve true
    return true;
}

void Solucion::imprimir(const Instancia& instancia) const {
    // Imprime la solución (los índices)
    cout << "Seleccion: ";
    for (int i = 0; i < cantidad(); i++) {
        cout << _indices[i];
        if (i < cantidad() - 1) {
            cout << " ";
        }
    }
    cout << "\n";
    // Imprime el costo total de la solución 
    cout << "Costo: " << costo(instancia) << "\n";
}

void Solucion::guardar(const std::string& ruta) const {
    // Escribe la seleección de indices (solución) en un archivo de texto, en la ruta 
    // que se pasa como parámetro
    ofstream archivo(ruta);
    for (int i = 0; i < cantidad(); i++) {
        archivo << _indices[i];
        if (i < cantidad() - 1) {
            archivo << " ";
        }
    }
    archivo << "\n";
}




