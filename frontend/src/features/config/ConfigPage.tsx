import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { getAreas, getTipos, api } from "@/api";

interface Area {
  codigo: string;
  nombre: string;
  tipo: string | null;
  activa: boolean;
}
interface Tipo {
  codigo: string;
  nombre: string;
  area_tipica_codigo: string | null;
  activo: boolean;
}

export function ConfigPage() {
  const qc = useQueryClient();
  const { data: areas } = useQuery<Area[]>({ queryKey: ["areas"], queryFn: getAreas });
  const { data: tipos } = useQuery<Tipo[]>({ queryKey: ["tipos"], queryFn: getTipos });
  const [nuevoTipo, setNuevoTipo] = useState({ codigo: "", nombre: "" });

  const crearTipo = async () => {
    if (!nuevoTipo.codigo || !nuevoTipo.nombre) return;
    await api.post("/config/tipos", nuevoTipo);
    setNuevoTipo({ codigo: "", nombre: "" });
    qc.invalidateQueries({ queryKey: ["tipos"] });
  };

  const exportar = async () => {
    const resp = await api.get("/config/export", { responseType: "blob" });
    const url = URL.createObjectURL(resp.data);
    const a = document.createElement("a");
    a.href = url;
    a.download = "config_clasifica.yaml";
    a.click();
  };

  return (
    <div className="grid grid-cols-2 gap-6">
      <section className="rounded-lg border bg-white p-4">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-semibold">Áreas ({areas?.length ?? 0})</h2>
          <button onClick={exportar} className="text-sm text-blue-600 hover:underline">
            Exportar config YAML
          </button>
        </div>
        <ul className="max-h-96 space-y-1 overflow-auto text-sm">
          {areas?.map((a) => (
            <li key={a.codigo} className="flex justify-between border-b py-1">
              <span>
                <code className="text-xs text-slate-500">{a.codigo}</code> {a.nombre}
              </span>
              {!a.activa && <span className="text-xs text-red-500">inactiva</span>}
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-lg border bg-white p-4">
        <h2 className="mb-3 font-semibold">Tipos documentales ({tipos?.length ?? 0})</h2>
        <div className="mb-3 flex gap-2">
          <input
            className="w-20 rounded border px-2 py-1 text-sm"
            placeholder="COD"
            value={nuevoTipo.codigo}
            onChange={(e) => setNuevoTipo({ ...nuevoTipo, codigo: e.target.value.toUpperCase() })}
          />
          <input
            className="flex-1 rounded border px-2 py-1 text-sm"
            placeholder="Nombre del tipo"
            value={nuevoTipo.nombre}
            onChange={(e) => setNuevoTipo({ ...nuevoTipo, nombre: e.target.value })}
          />
          <button onClick={crearTipo} className="rounded bg-blue-600 px-3 py-1 text-sm text-white">
            Añadir
          </button>
        </div>
        <ul className="max-h-80 space-y-1 overflow-auto text-sm">
          {tipos?.map((t) => (
            <li key={t.codigo} className="flex justify-between border-b py-1">
              <span>
                <code className="text-xs text-slate-500">{t.codigo}</code> {t.nombre}
              </span>
              <span className="text-xs text-slate-400">{t.area_tipica_codigo}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
