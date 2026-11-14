import { useEffect, useState } from "react";

type Summary = { n: number; total: number; media: number; objetivo: number };
type Report = {
  version: string;
  ultimo_sorteo: number;
  fecha_ultimo: string;
  registros: number;
  estrategia: string;
  azar_media: number;
  objetivo: number;
  p_objetivo: number;
  seleccion: Record<string, Summary>;
  validacion_exploratoria: Record<string, Summary>;
  lineas: Record<string, number[]>;
  contraste_media: { exact_p: number; monte_carlo_p: number; simulations: number };
  diagnostico_sesgo: { numero: number; apariciones: number; esperado: number; p_bonferroni: number; alerta: boolean }[];
  advertencia: string;
};

export default function ChileDashboard() {
  const [game, setGame] = useState("loto");
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setReport(null);
    setError("");
    fetch("/api/chile/analysis?game=" + game, { signal: controller.signal })
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "No se pudo analizar el historial");
        return data as Report;
      })
      .then((data) => { if (!controller.signal.aborted) setReport(data); })
      .catch((e: unknown) => { if (!controller.signal.aborted) setError(e instanceof Error ? e.message : String(e)); });
    return () => controller.abort();
  }, [game, refresh]);
  return (
    <section style={{padding: "1rem", maxWidth: 1100, margin: "auto"}}>
      <h2>Lotto Predictor Chile</h2>
      <p>Resultados secundarios pendientes de cotejo oficial. Análisis experimental, no garantiza premios.</p>
      <label>Juego: <select value={game} onChange={(e) => setGame(e.target.value)}>
        <option value="loto">Loto 6/41</option><option value="kino">Kino 14/25</option>
      </select></label>{" "}
      <button onClick={() => setRefresh((n) => n+1)}>Recalcular</button>
      {error && <p role="alert">Error: {error}. Inicie el servicio con <code>py chile/app.py</code>.</p>}
      {!report && !error && <p role="status">Calculando análisis…</p>}
      {report && <>
        <h3>Historial y prueba cronológica</h3>
        <p>{report.registros} sorteos · último #{report.ultimo_sorteo}, {report.fecha_ultimo} · modelo {report.estrategia}</p>
        <p>Media teórica aleatoria: {report.azar_media.toFixed(3)} · p exacto para media: {report.contraste_media.exact_p.toFixed(4)} · p Monte Carlo: {report.contraste_media.monte_carlo_p.toFixed(4)}.</p>
        <p>{report.advertencia}</p>
        <div style={{overflowX:"auto"}}><table style={{width:"100%", textAlign:"left"}}><thead><tr><th>Modelo</th><th>Selección</th><th>Validación</th><th>≥{report.objetivo}</th></tr></thead><tbody>
        {Object.entries(report.validacion_exploratoria).map(([name,row]) => <tr key={name}><td>{name===report.estrategia ? name+" (seleccionado)" : name}</td><td>{report.seleccion[name].media.toFixed(3)}</td><td>{row.media.toFixed(3)}</td><td>{row.objetivo}/{row.n}</td></tr>)}
        </tbody></table></div>
        <h3>Diagnóstico marginal de bolillas</h3>
        <p>No establece causalidad física. Contrastes corregidos por comparaciones múltiples.</p>
        <div style={{overflowX:"auto"}}><table style={{width:"100%",textAlign:"left"}}><thead><tr><th>Número</th><th>Apariciones</th><th>Esperadas</th><th>p corregido</th></tr></thead><tbody>
        {report.diagnostico_sesgo.map((row) => <tr key={row.numero}><td>{row.numero}</td><td>{row.apariciones}</td><td>{row.esperado.toFixed(1)}</td><td>{row.p_bonferroni.toFixed(4)}{row.alerta ? " · revisar" : ""}</td></tr>)}
        </tbody></table></div>
      </>}
    </section>
  );
}
