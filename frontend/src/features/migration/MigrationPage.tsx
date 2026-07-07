import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { crearMigracion, listMigraciones, pausarJob, reanudarJob } from "@/api";

interface Job {
  id: string;
  ruta_origen: string;
  total_documentos: number;
  procesados: number;
  exitosos: number;
  en_revision: number;
  erroneos: number;
  estado: string;
}

export function MigrationPage() {
  const [ruta, setRuta] = useState("");
  const { data: jobs, refetch } = useQuery<Job[]>({
    queryKey: ["migraciones"],
    queryFn: listMigraciones,
    refetchInterval: 2000,
  });

  const iniciar = async () => {
    if (!ruta) return;
    await crearMigracion(ruta);
    setRuta("");
    refetch();
  };

  return (
    <div className="space-y-6">
      <div className="rounded-lg border bg-white p-4">
        <h2 className="mb-3 font-semibold">Migración masiva de documentos históricos</h2>
        <p className="mb-2 text-sm text-slate-500">
          Indica la ruta de la carpeta (en el servidor) con los PDFs a clasificar en lote.
        </p>
        <div className="flex gap-2">
          <input
            className="flex-1 rounded border px-3 py-2"
            placeholder="/data/historico/2024"
            value={ruta}
            onChange={(e) => setRuta(e.target.value)}
          />
          <button onClick={iniciar} className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700">
            Iniciar migración
          </button>
        </div>
      </div>

      <div className="rounded-lg border bg-white p-4">
        <h3 className="mb-3 font-semibold">Trabajos de migración</h3>
        <div className="space-y-3">
          {jobs?.map((j) => (
            <JobRow key={j.id} job={j} onChange={refetch} />
          ))}
          {!jobs?.length && <p className="text-sm text-slate-400">Sin migraciones aún.</p>}
        </div>
      </div>
    </div>
  );
}

function JobRow({ job, onChange }: { job: Job; onChange: () => void }) {
  const pct = job.total_documentos ? Math.round((job.procesados / job.total_documentos) * 100) : 0;
  const toggle = async () => {
    if (job.estado === "pausado") await reanudarJob(job.id);
    else await pausarJob(job.id);
    onChange();
  };
  return (
    <div className="rounded border p-3">
      <div className="flex items-center justify-between">
        <span className="truncate text-sm font-medium">{job.ruta_origen}</span>
        <span className="text-xs uppercase text-slate-500">{job.estado}</span>
      </div>
      <div className="mt-2 h-2 w-full overflow-hidden rounded bg-slate-100">
        <div className="h-full bg-blue-500" style={{ width: `${pct}%` }} />
      </div>
      <div className="mt-1 flex justify-between text-xs text-slate-500">
        <span>
          {job.procesados}/{job.total_documentos} · ok {job.exitosos} · rev {job.en_revision} · err {job.erroneos}
        </span>
        {["en_curso", "pausado"].includes(job.estado) && (
          <button onClick={toggle} className="text-blue-600 hover:underline">
            {job.estado === "pausado" ? "Reanudar" : "Pausar"}
          </button>
        )}
      </div>
    </div>
  );
}
