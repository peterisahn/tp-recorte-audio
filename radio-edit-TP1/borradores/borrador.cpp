// Borrador de reconstruir_solucion_pd

// // Función auxiliar que recorre una fila del memo para algún nivel n' <= n
// // y devuelve los índices tal que el costo es el mínimo de esa fila
// int minimo (const vector<float> &costos){
//     // Inicializamos res en 0, que devuelve el índice del pulso
//     int res = 0;
//     // Inicializamos min en infinito
//     float min = numeric_limits<float>::infinity();

//     // Recorremos el vector de costos
//     int i = 0;
//     float costo = 0.0;
//     while (i<costos.size()){
//          if (costo < min);
//             min = costo;
//             res = i;
//     }
//     return res;
// }
// Solucion reconstruir_solucion_pd (const Instancia& instancia, vector<vector<float>> memo, float costo_min, int n, int k){
//     // Como vamos a recorrer el memo desde la posición n,k (ult posición) y recorremos hacia arriba a la izquierda
//     // los indices van a estar desordenados. Entonces guardamos temporalmente los indices en un vector y luego lo copiamos a solución
//     vector<int> indices = {};

//     // Inicializamos las variables j,t
//     int j = n;
//     int t = k;

//     // Recorremos hasta que lleguemos a la posición 0,0
//     while (j!=0 and t!=0){
//         // Copiamos los costos de la fila j del memo desde el pulso t=0 hasta el t-esimo pulso
//         vector<float> fila (memo[j].begin(), memo[j].begin()+t);
//         int min = minimo(fila);

//         // Si la posición j,t tiene costo igual que la posición j-1, t-1 más el costo de ir desde t-1 hasta t
//         // Entonces quiere decir que se usó el pulso t en la solución
//         if (memo[j][t]== memo[j-1][t-1]+instancia.costo(t-1, t)){
//             indices.push_back(t);
//             j--;
//             t--;
//         }
//         // En cambio si tiene el mismo costo que la posición n-1, t quiere decir que el t-ésimo pulso no se está usando
//         if (memo[j][t] == memo[j-1][t]){
//             j--;
//             t--;
//         }
//     }

//     // Ordenamos los índices de menor a mayor 
//     sort(indices.begin(), indices.end());

//     // Copiamos los índices a solución
//     Solucion solucion;
//     for (int indice : indices){
//         solucion.agregar(indice);
//     }

//     return solucion;
// }