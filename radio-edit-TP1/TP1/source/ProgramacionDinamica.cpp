#include "ProgramacionDinamica.h"
#include <vector> 
#include <limits>
#include <algorithm>

using namespace std;

Solucion reconstruir_solucion_pd (const Instancia& instancia, vector<vector<float>> memo, float costo_min, int n, int k){
    // Como vamos a recorrer el memo desde la posición n,k (ult posición) y recorremos hacia arriba a la izquierda
    // los indices van a estar desordenados. Entonces guardamos temporalmente los indices en un vector y luego lo copiamos a solución
    vector<int> indices = {};

    // Inicializamos las variables j,t
    int j = n;
    int t = k;

    // Recorremos hasta que lleguemos a la posición 0,0
    while (j!=0 and t!=0){
        // Si la posición j,t tiene costo igual que la posición j-1, t-1 más el costo de ir desde t-1 hasta t
        // Entonces quiere decir que se usó el pulso t en la solución
        if (memo[j][t]== memo[j-1][t-1]+instancia.costo(t-1, t)){
            indices.push_back(t);
            j--;
            t--;
        }
        // En cambio si tiene el mismo costo que la posición n-1, t quiere decir que el t-ésimo pulso no se está usando
        if (memo[j][t] == memo[j-1][t]){
            j--;
            t--;
        }
    }

    // Ordenamos los índices de menor a mayor 
    sort(indices.begin(), indices.end());

    // Copiamos los índices a solución
    Solucion solucion;
    for (int indice : indices){
        solucion.agregar(indice);
    }

    return solucion;
}

float minimo (float a, float b){
    if (a>b){
        return a;
    }else{
        return b;
    }
}

float pd (const Instancia& instancia, int j, int t, vector<vector<float>>& memo){
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
    // Si ya visitamos la celda j,t , pero no es posible esa combinación (por ej. t>j), entonces devolvemos infinito
    float res = numeric_limits<float>::infinity();

    // Para cada i (i<j) que puede elegir de los pulsos restantes hasta la posición j (actual), usando t-1 pulsos (el pulso t es el que va desde i hasta j)
    for (int i = 2; i< j-1; i++){
        // Guardamos en la celda el mínimo entre lo que ya estaba guardado en la celda (inicialmente infinito), con lo que
        // te devuelve la recursión usando t-1 pulsos hasta el pulso i, más el costo de ir desde i hasta j
        res = minimo(res, pd(instancia, i, t-1, memo)+instancia.costo(i,j));
    }

    // Guardamos (y retornamos) finalmente en res el costo acumulado mínimo de tomar t pulsos, hasta el pulso j 
    memo[j][t] = res;
    return res;        
}


Solucion ProgramacionDinamica::resolver(const Instancia& instancia) {
    // Inicializamos la variable global que va a devolver la solución
    Solucion solucion;

    // Agregamos el primer pulso
    solucion.agregar(1);

    // Inicializamos las variables enteras k,n
    int k = instancia.k();
    int n = instancia.n();
    
    // Creamos el memo de tamaño (n+1, k+1) = (filas, columnas), inicializando las celdas en -1.0, que quiere decir que todavía no las visitamos
    vector<vector<float>> memo(n+1, vector<float>(k+1, -1.0));

    // Llamamos a un función auxiliar que devuelve el costo mínimo para k pulsos usando pd
    float costo_min = pd (instancia, n, k, memo);

    // Llamamos a una función auxiliar, que reconstruye la solución (los índices) a partir del memo
    solucion = reconstruir_solucion_pd (instancia, memo, costo_min, n,k);

    return solucion;
}
