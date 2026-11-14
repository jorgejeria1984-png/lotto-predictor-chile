# Registro histórico inicial — 14 de noviembre de 2026

Son resultados publicados por fuentes secundarias, no una exportación oficial auditada. Cada fila conserva su fuente. Solo juego principal: sin comodín, recargado, ReKino, etc. No hay datos sintéticos.

- Loto: 104 sorteos 5400–5503, 17-03-2026 a 12-11-2026.
- Kino: 81 sorteos 3225–3305, 10-05-2026 a 13-11-2026.

Validación estructural: fechas e identificadores consecutivos, cantidad exacta de bolillas distintas y rango. Aún falta contrastar cada registro contra el operador oficial. No se afirma que el archivo sea completo.

## Comandos desde la raíz del fork

    py chile/history.py audit --game loto
    py chile/history.py audit --game kino
    py chile/history.py analyze --game loto
    py chile/history.py merge --game kino --file nuevos.csv --source https://www.loteria.cl/

El archivo entrante usa los encabezados de las plantillas, con source_url adicional si procede. Solo registre URL real del resultado consultado. Rechaza conflictos para el mismo identificador y no rellena ausencias. Analiza únicamente el bloque reciente consecutivo si alcanza 80 sorteos. La restricción de era usa 2935 (Loto) y 799 (Kino) como límites indicados por Indicadores y Datos; verificar con archivos oficiales antes de extender a esas fechas.

## Primer backtest Loto

104 registros. Calentamiento 50, selección 36 y validación cronológica 18. Estrategia seleccionada por media del segmento de selección: reciente_25. Media de selección: 1.0556. Media de validación: 1.0556. Referencia aleatoria teórica: 0.8780. En validación, 2 de 18 sorteos con 3+ aciertos; probabilidad aleatoria de 3+ por sorteo 0.0311441; prueba binomial unilateral para ese objetivo p=0.1068151. No demuestra ventaja predictiva. El tamaño del segmento es insuficiente para conclusiones robustas. No reoptimizar usando el segmento de validación. Kino ya alcanza el mínimo: 81 registros.

## Fuentes

- https://indicadoresydatos.cl/azar/estadisticas-loto-kino
- https://loterator.com/cl/loto/sorteos/
- https://loterator.com/cl/loto/sorteos/?page=2
- https://www.lotochile.com/loto/2026
- https://lotero.cl/resultados-kino/todos/
- https://sortuo.cl/

La descarga automática de sitios externos queda pendiente: el entorno de ejecución local utilizado no tiene acceso directo a esas páginas.

## Ampliación y backtest Kino (14-11-2026)

Se agregan 45 sorteos publicados por Sortuo (páginas 2–10), con comprobaciones parciales contra LoterAtor y Lotero. 50 sorteos de calentamiento, 20 de selección, 11 de validación. reciente_100 empata con histórica y bayes (mismo orden con menos de 100 sorteos). Media de selección 7.9; validación 93/11 = 8.454545; azar teórico 7.84; 1 de 11 con 10+ aciertos; p binomial 0.6401968. No hay ventaja demostrada. 

## Comparación de medias

uncertainty.py calcula la cola exacta por convolución hipergeométrica y la contrasta con 100.000 simulaciones del total de aciertos bajo sorteos independientes justos, semilla 42. Loto (19 en 18): p exacto 0.2133854, Monte Carlo 0.21252. Kino (93 en 11): p exacto 0.0663509, Monte Carlo 0.06547. Son diagnósticos exploratorios de la validación ya usada, no una nueva confirmación independiente. No hay resultados significativos al 5%. Consultar las fuentes oficiales antes de considerar el archivo verificado. 
