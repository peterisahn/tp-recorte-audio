#include "ProgramacionDinamica.h"
#include <vector> 
#include <limits>
#include <algorithm>

using namespace std;

// Funcion que reconstruye la solución. Pero como fuimos guardando los indices ('padre') a medida
// que ibamos construyendo la solución, la tarea de reconstrucción es más simple.
Solucion reconstruir_solucion_pd (const vector<vector<int>> &padre, int n, int k){
    vector<int> indices;
    int j = n;
    int t = k;

    while (t > 1) {
        indices.push_back(j);
        j = padre[j][t];
        t--;
    }
    indices.push_back(1);   // el pulso 1 siempre es el inicio

    reverse(indices.begin(), indices.end());  // los juntamos en orden inverso, hay que darlos vuelta

    Solucion solucion;
    for (int indice : indices) solucion.agregar(indice);
    return solucion;
}

// Función auxiliar que devuelve el mínimo entre dos floats
float minimo (float a, float b){
    if (a>b){
        return b;
    }else{
        return a;
    }
}

float pd (const Instancia& instancia, int j, int t, vector<vector<float>>& memo, vector<vector<int>> &padre){
    // aclaración: j,t son variables (índices) que representan sub-instancias del problema original n,k respectivamente

    // Casos base:
    // Si t>j:
    // Si se quiere tomar t pulsos, de j pulsos totales tal que t>j -> es imposible. Devolvemos infinito
    if (t>j){
        return numeric_limits<float>::infinity();
    }else{
        // Si t<j:
        // Si t==2, tomamos el primer y el último pulso j (con t<j)
        if (t==2){
            padre[j][2] = 1;
            return instancia.costo(1,j);
        }

    }

    // Si ya calculamos el costo acumulado para t pulsos tomados de j pulsos (t<=j), devolvemos lo que hay en el memo
    // Idea: como existe superposición de estados buscamos evitar calular varias veces una misma sub-instancia)
    if (memo[j][t]>=0){
        return memo[j][t];  
    }

    // Inicializamos la variable de retorno res en infinito, que almacena los valores que van a ir en cada celda y finalmente
    // de la celda de interés: memo[n][k]
    // Si ya visitamos la celda j,t , pero no es posible esa combinación (por ej. t>j), entonces devuelve infinito
    float res = numeric_limits<float>::infinity();
    // Inicializamos una variable que guarde el índice del pulso desde cuyo costo hacia el siguiente sea el mínimo
    int guardar_pos = -1;
    // Para cada i (i<j) que puede elegir de los pulsos restantes hasta la posición j (actual), usando t-1 pulsos (el pulso t es el que va desde i hasta j)
    for (int i = 2; i< j-1; i++){
        // Guardamos en la celda el mínimo entre lo que ya estaba guardado en la celda (inicialmente infinito), con lo que
        // te devuelve la recursión usando t-1 pulsos hasta el pulso i, más el costo de ir desde i hasta j
        float nuevo_res = minimo(res, pd(instancia, i, t-1, memo, padre)+instancia.costo(i,j));
        if (nuevo_res != res){
            guardar_pos = i; // Si cambio -> quiere decir que la recursión encontro una solución mejor
        }
        res = nuevo_res;
    }

    // Guardamos (y retornamos) finalmente en res el costo acumulado mínimo de tomar t pulsos, hasta el pulso j 
    memo[j][t] = res;
    // Guardamos el 'padre' de la instancia j,t
    padre[j][t] = guardar_pos;
    return res;        
}


Solucion ProgramacionDinamica::resolver(const Instancia& instancia) {
    // Inicializamos la variable global que va a devolver la solución
    Solucion solucion;

    // Inicializamos las variables enteras k,n
    int k = instancia.k();
    int n = instancia.n();
    
    // Creamos el memo de tamaño (n+1, k+1) = (filas, columnas), inicializando las celdas en -1.0, que quiere decir que todavía no las visitamos
    vector<vector<float>> memo(n+1, vector<float>(k+1, -1.0));
    // Creamos una tabla que guarda quien es el 'padre' para cada instancia j,t
    vector<vector<int>> padre(n+1, vector<int>(k+1, -1));

    // Llamamos a un función auxiliar que devuelve el costo mínimo para k pulsos usando pd. Además va guardando en 'indices' los indices
    // a medida que construye la solución (por eso se pasa 'inidices' como referencia en la función)
    float costo_min = pd (instancia, n, k, memo, padre);

    // Llamamos a una función auxiliar, que reconstruye la solución (los índices) a partir del memo
    solucion = reconstruir_solucion_pd (padre, n, k);

    return solucion;
}
