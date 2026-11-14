# Registro histórico inicial — 14 de noviembre de 2026

Son resultados publicados por fuentes secundarias, no una exportación oficial auditada. Cada fila conserva su fuente. Solo juego principal: sin comodín, recargado, ReKino, etc. No hay datos sintéticos.

- Loto: 104 sorteos 5400–5503, 17-03-2026 a 12-11-2026.
- Kino: 36 sorteos 3270–3305, 23-08-2026 a 13-11-2026.

Validación estructural: fechas e identificadores consecutivos, cantidad exacta de bolillas distintas y rango. Aún falta contrastar cada registro contra el operador oficial. No se afirma que el archivo sea completo.

## Comandos desde la raíz del fork

    py chile/history.py audit --game loto
    py chile/history.py audit --game kino
    py chile/history.py analyze --game loto
    py chile/history.py merge --game kino --file nuevos.csv --source https://www.loteria.cl/

El archivo entrante usa los encabezados de las plantillas, con source_url adicional si procede. Solo registre URL real del resultado consultado. Rechaza conflictos para el mismo identificador y no rellena ausencias. Analiza únicamente el bloque reciente consecutivo si alcanza 80 sorteos. La restricción de era usa 2935 (Loto) y 799 (Kino) como límites indicados por Indicadores y Datos; verificar con archivos oficiales antes de extender a esas fechas.

## Primer backtest Loto

104 registros. Calentamiento 50, selección 36 y validación cronológica 18. Estrategia seleccionada por media del segmento de selección: reciente_25. Media de selección: 1.0556. Media de validación: 1.0556. Referencia aleatoria teórica: 0.8780. En validación, 2 de 18 sorteos con 3+ aciertos; probabilidad aleatoria de 3+ por sorteo 0.0311441; prueba binomial unilateral para ese objetivo p=0.1068151. No demuestra ventaja predictiva. El tamaño del segmento es insuficiente para conclusiones robustas. No reoptimizar usando el segmento de validación. Kino sigue por debajo del mínimo.

## Fuentes

- https://indicadoresydatos.cl/azar/estadisticas-loto-kino
- https://loterator.com/cl/loto/sorteos/
- https://loterator.com/cl/loto/sorteos/?page=2
- https://www.lotochile.com/loto/2026
- https://lotero.cl/resultados-kino/todos/
- https://sortuo.cl/

La descarga automática de sitios externos queda pendiente: el entorno de ejecución local utilizado no tiene acceso directo a esas páginas.
