import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { searchDocumentos, DocumentOut, Paginated, api } from "@/api";

const MODOS = [
  { id: "hibrido", label: "Inteligente (híbrido)" },
  { id: "semantico", label: "Semántico (por concepto)" },
  { id: "exacto", label: "Exacto (palabra clave)" },
];

export function ExplorerPage() {
  const [q, setQ] = useState("");
  const [modo, setModo] = useState("hibrido");
  const [area, setArea] = useState("");
  const [tipo, setTipo] = useState("");
  const [anio, setAnio] = useState("");
  const [buscar, setBuscar] = useState(false);
  const [seleccion, setSeleccion] = useState<Set<string>>(new Set());

  const { data, isFetching } = useQuery<Paginated<DocumentOut>>({
    queryKey: ["search", q, modo, area, tipo, anio],
    queryFn: () =>
      searchDocumentos({
        q,
        modo,
        area: area || undefined,
        tipo: tipo || undefined,
        anio: anio || undefined,
      }),
    enabled: buscar && q.length > 0,
  });

  const exportar = async () => {
    const resp = await api.post(
      "/exports",
      { document_ids: [...seleccion] },
      { responseType: "blob" },
    );
    const url = URL.createObjectURL(resp.data);
    const a = document.createElement("a");
    a.href = url;
    a.download = "export_clasifica.zip";
    a.click();
  };

  const toggle = (id: string) => {
    const s = new Set(seleccion);
    s.has(id) ? s.delete(id) : s.add(id);
    setSeleccion(s);
  };

  return (
    <div className="space-y-4">
      <div className="rounded-lg border bg-white p-4">
        <div className="flex gap-2">
          <input
            className="flex-1 rounded border px-3 py-2"
            placeholder="Buscar por asunto, contenido o concepto…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && setBuscar(true)}
          />
          <button onClick={() => setBuscar(true)} className="rounded bg-blue-600 px-4 py-2 text-white">
            Buscar
          </button>
        </div>
        <div className="mt-3 flex flex-wrap gap-2 text-sm">
          <select value={modo} onChange={(e) => setModo(e.target.value)} className="rounded border px-2 py-1">
            {MODOS.map((m) => (
              <option key={m.id} value={m.id}>
                {m.label}
              </option>
            ))}
          </select>
          <input className="w-28 rounded border px-2 py-1" placeholder="Área" value={area} onChange={(e) => setArea(e.target.value)} />
          <input className="w-28 rounded border px-2 py-1" placeholder="Tipo" value={tipo} onChange={(e) => setTipo(e.target.value)} />
          <input className="w-24 rounded border px-2 py-1" placeholder="Año" value={anio} onChange={(e) => setAnio(e.target.value)} />
          {seleccion.size > 0 && (
            <button onClick={exportar} className="rounded bg-slate-700 px-3 py-1 text-white">
              Exportar ({seleccion.size}) ZIP+CSV
            </button>
          )}
        </div>
      </div>

      <div className="rounded-lg border bg-white">
        {isFetching && <p className="p-4 text-sm text-slate-500">Buscando…</p>}
        <table className="w-full text-sm">
          <thead className="border-b bg-slate-50 text-left text-slate-500">
            <tr>
              <th className="p-2"></th>
              <th className="p-2">Correlativo</th>
              <th className="p-2">Tipo</th>
              <th className="p-2">Área</th>
              <th className="p-2">Asunto</th>
              <th className="p-2">Año</th>
            </tr>
          </thead>
          <tbody>
            {data?.items.map((d) => (
              <tr key={d.id} className="border-b hover:bg-slate-50">
                <td className="p-2">
                  <input type="checkbox" checked={seleccion.has(d.id)} onChange={() => toggle(d.id)} />
                </td>
                <td className="p-2 font-mono text-xs">{d.correlativo ?? "—"}</td>
                <td className="p-2">{d.tipo_codigo}</td>
                <td className="p-2">{d.area_codigo}</td>
                <td className="p-2">{d.asunto}</td>
                <td className="p-2">{d.anio_documento}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {data && !data.items.length && <p className="p-4 text-sm text-slate-400">Sin resultados.</p>}
        {data && <p className="p-2 text-xs text-slate-400">{data.total} resultado(s)</p>}
      </div>
    </div>
  );
}
