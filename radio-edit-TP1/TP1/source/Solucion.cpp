#include "Solucion.h"

#include "Instancia.h"
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

// Armamos funciones auxiliares con las condiciones que tiene que cumplir 'instancia' para que sea válida

bool primer_y_ultimo_ordenados(const vector<int> &indices, int n){

     if ( indices[0] == 0 and indices[indices.size()-1] == n){
        return true;
     }else{
        return false;
     }
}

bool esta_ordenado (const vector<int> &indices){
    int i = 0;
    while (i<indices.size()){
        if (indices[i]<indices[i+1]){
            i+=1;
        }else{
            return false;
        }
    }
    return true;
}

bool Solucion::esValida(const Instancia& instancia) const {
    // Para que sea considerado una solución válida debe cumplir:
    // - El primer pulso y el último deben mantenerse
    // - El tamaño de la solución debe ser exactamente k
    // - Los índices en _indices deben estar ordenados

    if (primer_y_ultimo_ordenados(_indices, instancia.n()-1) and _indices.size() == instancia.k() and esta_ordenado(_indices)){
        return true;
    }
    return false;
}

// bool Solucion::esValida(const Instancia& instancia) const {
//     if (cantidad() != instancia.k()) {
//         return false;
//     }
//     if (_indices[0] != 1) {
//         return false;
//     }
//     if (_indices[cantidad() - 1] != instancia.n()) {
//         return false;
//     }
//     for (int i = 0; i < cantidad() - 1; i++) {
//         if (_indices[i] >= _indices[i + 1]) {
//             return false;
//         }
//     }
//     return true;
// }

void Solucion::imprimir(const Instancia& instancia) const {

    cout << "Seleccion: ";
    for (int i = 0; i < cantidad(); i++) {
        cout << _indices[i];
        if (i < cantidad() - 1) {
            cout << " ";
        }
    }
    cout << "\n";
    cout << "Costo: " << costo(instancia) << "\n";
}

void Solucion::guardar(const std::string& ruta) const {
    ofstream archivo(ruta);
    for (int i = 0; i < cantidad(); i++) {
        archivo << _indices[i];
        if (i < cantidad() - 1) {
            archivo << " ";
        }
    }
    archivo << "\n";
}




