# Lotto Predictor Chile — módulo experimental

Adaptación independiente de los conceptos estadísticos del proyecto original. No sustituye ni modifica el backend .NET, React ni las bases SQLite originales. Solo utiliza la biblioteca estándar de Python 3.10 o posterior. No requiere claves ni servicios de terceros.

## Ejecutar en Windows

Desde la raíz del fork, en la rama chile-loto-kino, ejecute en PowerShell:

    py chile/app.py

Abra http://127.0.0.1:8765 en el navegador. Seleccione el juego y pegue un CSV de resultados oficiales del juego principal. El servidor escucha solo en la interfaz local. Para cerrar, Ctrl+C.

## CLI

    py chile/app.py --game loto --csv loto.csv
    py chile/app.py --game kino --csv kino.csv

Los archivos loto_plantilla.csv y kino_plantilla.csv contienen únicamente encabezados. Añada una fila por sorteo con fecha ISO (AAAA-MM-DD), identificador de sorteo y números principales, sin comodín, ReKino ni otros juegos complementarios. No se incluyen resultados inventados ni se realiza descarga automática. Solo use sorteos del formato actual; no mezcle eras incompatibles. Se validan números repetidos, rangos, identificadores y cronología, pero no la autenticidad ni la ausencia de sorteos intermedios. Las fuentes oficiales para comprobar resultados son https://www.polla.cl/ y https://www.loteria.cl/.

## Evaluación

Loto 6 de 41, Kino 14 de 25. Mínimo 80 sorteos; primeros 50 como calentamiento, dos tercios de los restantes para elegir por promedio de aciertos y último tercio para evaluación cronológica separada. Cada predicción utiliza solo resultados anteriores. Se reporta una referencia aleatoria reproducible, media teórica hipergeométrica, tasa de 3+ (Loto) o 10+ (Kino) y prueba binomial unilateral para esa tasa. Estos umbrales son decisiones experimentales, no afirmaciones de premios oficiales. La selección por media y la prueba de tasa son métricas distintas. El modelo no demuestra capacidad predictiva hasta contar con evidencia independiente; incluso una prueba positiva requiere replicación. El modelo bayesiano con prior común produce el mismo orden que la frecuencia histórica (no es evidencia independiente). No incorpora aún aprendizaje AdaGrad, optimización evolutiva, persistencia, integración React/.NET ni importación automática.

## Pruebas

    cd chile
    py -m unittest -v

Las pruebas usan datos sintéticos solo para validar el funcionamiento, no para estimar eficacia sobre sorteos reales. No redistribuye código del original: este módulo es una implementación separada en Python de métodos generales.
