# Lotto Predictor Chile — experimental

Loto principal 6/41 y Kino principal 14/25. El motor Python no reemplaza el almacenamiento original de los juegos británicos. La pestaña Chile de React consulta un gateway de solo lectura en ASP.NET (.NET 10), que comunica con el servicio Python local. No hay capacidad predictiva demostrada frente al azar.

## Inicio rápido (Windows): dashboard autónomo

Desde la raíz del repositorio ejecute solamente:

    py chile/app.py

Abra http://127.0.0.1:8765. El dashboard 2.0 carga los históricos locales automáticamente. Selector Loto/Kino, comparación de modelos, combinaciones experimentales, frecuencias históricas y últimos 25 sorteos, Monte Carlo 100.000 ensayos, diagnóstico de sesgo, historial paginado y consulta/registro prospectivo. El botón Buscar nuevos resultados descarga candidatos; solo tras comprobarlos con los operadores oficiales puede incorporarlos al CSV local. La validación del parser con HTML real sigue pendiente. LSTM es opcional mediante la casilla y requiere PyTorch instalado; el REST de solo lectura sigue siendo compatible con el gateway anterior. No se necesita React ni .NET para este modo. Los cambios del historial y el registro SQLite son locales, no se sincronizan automáticamente con GitHub.

## Modo integrado alternativo (React y .NET)

Desde la raíz del repositorio, ejecute en tres terminales:

    py chile/app.py
    dotnet run --project backend/LottoPredictor.Api --launch-profile http
    cd frontend
    npm ci
    npm run dev

Requiere Python 3.10+, SDK .NET 10 y Node 22. Abra http://127.0.0.1:5173 y seleccione la pestaña Chile. El dashboard utiliza http://127.0.0.1:5080/api/chile/analysis?game=loto (Vite reenvía /api); el gateway consulta el servicio Python en 127.0.0.1:8765. También puede usar directamente http://127.0.0.1:8765 para el dashboard autónomo. No exponer los servidores de desarrollo a Internet. Si usa los otros juegos, configure sus claves locales según RUNNING.md del proyecto original. El gateway Chile solo admite GET y no modifica datos.

## Datos y auditoría

    py chile/history.py audit --game loto
    py chile/history.py audit --game kino
    py chile/history.py analyze --game loto

Incluye 104 sorteos Loto (5400–5503) y 81 Kino (3225–3305), fuentes secundarias pendientes de cotejo oficial fila por fila. Se comprobó que los últimos resultados coinciden con otras publicaciones. No se incluyen comodín ni complementarios. No se ha completado el histórico de las eras actuales. Fuentes de consulta: https://www.polla.cl/ y https://www.loteria.cl/.

La fecha de cambio a 41 bolillas difiere entre fuentes (2931 vs 2935); conservamos el corte 2935 hasta resolverlo con actas oficiales. El descargador solo toma las tablas explícitas de los juegos modernos, no infiere resultados desde cifras dispersas del HTML. Su formato se prueba con fixtures; acceso y estructura de la página real aún deben confirmarse.

    py chile/fetch_history.py --game loto --output chile/staging/loto.csv
    py chile/fetch_history.py --game kino --output chile/staging/kino.csv

Verifique las filas contra los operadores antes de integrar:

    py chile/history.py merge --game loto --file chile/staging/loto.csv
    py chile/history.py merge --game kino --file chile/staging/kino.csv

El descargador no sustituye archivos existentes ni rellena ausencias. El flujo de GitHub Actions chile-history-candidates prepara candidatos diarios a las 04:30 UTC, cuando esté integrado en la rama por defecto y Actions habilitado; no hace commits ni altera el histórico. Los resultados se conservan como artefacto por 14 días. La descarga masiva de archivos antiguos sigue pendiente y no se deben eludir restricciones de los sitios.

## Modelos avanzados

    py chile/advanced.py --game loto
    py chile/advanced.py --game kino

11 estrategias base + logit marginal online (AdaGrad, regularización L2) + evolución de pesos de características (16 candidatos, cambios cada 8 sorteos). La opción LSTM agrega un modelo recurrente causal entrenado exclusivamente con sorteos previos:

    py -m pip install --index-url https://download.pytorch.org/whl/cpu torch
    py chile/advanced.py --game kino --lstm

El LSTM es opcional y no se ejecuta en el dashboard para evitar dependencias adicionales. Los modelos ordenan bolillas y seleccionan un conjunto de tamaño fijo; no interpretamos scores como probabilidades calibradas. Las decisiones de hiperparámetros fueron iniciales, no optimizadas sobre holdout. El módulo de sesgo analiza frecuencias marginales con p-valores binomiales conservadores y corrección Bonferroni; no identifica por sí mismo una causa física. Se requiere información de máquinas y bolillas para investigar sesgo físico.

50 sorteos de calentamiento, dos tercios del resto para escoger estrategia por media, último tercio para diagnóstico cronológico, con una referencia aleatoria reproducible. Hipergeométrica exacta y Monte Carlo contrastan media; objetivo 3+ / 10+ evaluado por cola binomial. Dado que ya se exploró este histórico durante el desarrollo, los resultados de todos los modelos nuevos se consideran exploratorios, incluso si son significativos. La confirmación debe ser prospectiva.

## Registro prospectivo con SQLite

Primero coteje todos los datos y verifique la fecha y hora oficial del siguiente sorteo. Use un deadline futuro con zona horaria explícita:

    py chile/prospective.py freeze --game loto --deadline AÑO-MES-DIAT21:00:00-03:00 --reviewed

Sustituya la fecha y el offset por los correctos para el próximo sorteo. Use el subcomando settle después de importar el resultado oficial:

    py chile/prospective.py settle --game loto --reviewed
    py chile/prospective.py report --game loto

Los registros incluyen cutoff, versión, hash de los resultados de entrenamiento, conjunto de modelos y estrategia seleccionada. La aplicación y triggers impiden UPDATE/DELETE, y notifican conflictos de históricos. La base SQLite local NO prueba inmutabilidad frente a un administrador ni garantiza que el reloj no fue cambiado: publique el hash del registro antes del sorteo en un sistema externo con sello temporal independiente para una prueba auditable. No se registra una predicción real automáticamente. No usar los diagnósticos acumulados como regla de parada repetida; predefinir horizonte de validación.

## Pruebas

    py -m unittest discover -s chile -v

Pruebas sintéticas de causalidad, rango, forma de datos, conflictos, exactitud y registro. CI prueba Python, compilación React, gateway .NET y LSTM (dependencia CPU en Pull Requests). No hay una prueba que garantice éxito en lotería.

## Pendientes

Ampliar históricos y verificar fuentes oficiales; confirmar el descargador contra HTML real; prueba prospectiva de horizonte pre-registrado y suficiente tamaño; integrar escritura autorizada y persistencia nativa si se requiere; desplegar con seguridad de producción. Los modelos adaptativos se reconstruyen al ejecutar el historial, no son un estado entrenado persistido entre reinicios. La migración completa a entidades C# de tamaño variable y el despliegue público quedan fuera de esta integración híbrida.
