import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { bandejaRevision, classifyDocumento, DocumentOut, Paginated } from "@/api";

export function ReviewPage() {
  const qc = useQueryClient();
  const { data } = useQuery<Paginated<DocumentOut>>({
    queryKey: ["revision"],
    queryFn: bandejaRevision,
    refetchInterval: 5000,
  });

  return (
    <div className="space-y-4">
      <h2 className="font-semibold">Bandeja de revisión ({data?.total ?? 0})</h2>
      <p className="text-sm text-slate-500">
        Documentos con baja confianza o clasificación ambigua. Corrige y guarda para reubicarlos
        y mejorar el clasificador (feedback loop).
      </p>
      {data?.items.map((doc) => (
        <ReviewCard
          key={doc.id}
          doc={doc}
          onSaved={() => qc.invalidateQueries({ queryKey: ["revision"] })}
        />
      ))}
      {!data?.items.length && (
        <p className="rounded-lg border bg-white p-6 text-slate-400">No hay documentos pendientes de revisión.</p>
      )}
    </div>
  );
}

function ReviewCard({ doc, onSaved }: { doc: DocumentOut; onSaved: () => void }) {
  const [tipo, setTipo] = useState(doc.tipo_codigo ?? "");
  const [area, setArea] = useState(doc.area_codigo ?? "");
  const [asunto, setAsunto] = useState(doc.asunto ?? "");
  const [justif, setJustif] = useState("");

  const mut = useMutation({
    mutationFn: () =>
      classifyDocumento(doc.id, {
        tipo_codigo: tipo,
        area_codigo: area,
        asunto,
        justificacion_operador: justif,
      }),
    onSuccess: onSaved,
  });

  return (
    <div className="grid grid-cols-2 gap-4 rounded-lg border bg-white p-4">
      <div>
        <p className="mb-2 text-sm font-medium">
          Confianza LLM: {doc.confianza != null ? `${Math.round(doc.confianza * 100)}%` : "—"}
        </p>
        {doc.justificacion_llm && (
          <p className="mb-2 rounded bg-amber-50 p-2 text-xs text-amber-800">
            Sugerencia: {doc.tipo_codigo}/{doc.area_codigo} — {doc.justificacion_llm}
          </p>
        )}
        <iframe
          title="preview"
          src={`/api/v1/documents/${doc.id}/preview`}
          className="h-64 w-full rounded border"
        />
      </div>
      <div className="space-y-2">
        <label className="block text-sm">
          Tipo
          <input className="mt-1 w-full rounded border px-2 py-1" value={tipo} onChange={(e) => setTipo(e.target.value)} />
        </label>
        <label className="block text-sm">
          Área
          <input className="mt-1 w-full rounded border px-2 py-1" value={area} onChange={(e) => setArea(e.target.value)} />
        </label>
        <label className="block text-sm">
          Asunto
          <input className="mt-1 w-full rounded border px-2 py-1" value={asunto} onChange={(e) => setAsunto(e.target.value)} />
        </label>
        <label className="block text-sm">
          Justificación (opcional)
          <input className="mt-1 w-full rounded border px-2 py-1" value={justif} onChange={(e) => setJustif(e.target.value)} />
        </label>
        <button
          onClick={() => mut.mutate()}
          disabled={mut.isPending}
          className="w-full rounded bg-green-600 py-2 text-white hover:bg-green-700 disabled:opacity-50"
        >
          {mut.isPending ? "Guardando…" : "Corregir y aprobar"}
        </button>
      </div>
    </div>
  );
}
