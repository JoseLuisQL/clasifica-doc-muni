import { useCallback, useEffect, useState } from "react";
import { useDropzone } from "react-dropzone";
import { uploadDocumento, getDocumento, classifyDocumento, DocumentOut } from "@/api";

export function UploadPage() {
  const [doc, setDoc] = useState<DocumentOut | null>(null);
  const [msg, setMsg] = useState("");

  const onDrop = useCallback(async (files: File[]) => {
    if (!files.length) return;
    setMsg("Subiendo y procesando…");
    const d = await uploadDocumento(files[0]);
    setDoc(d);
    // Escuchar progreso por WebSocket
    const ws = new WebSocket(
      `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/documents/${d.id}`,
    );
    ws.onmessage = (ev) => {
      const data = JSON.parse(ev.data);
      setMsg(`Estado: ${data.estado}`);
      if (["clasificado", "revision", "error"].includes(data.estado)) {
        getDocumento(d.id).then(setDoc);
        ws.close();
      }
    };
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    maxFiles: 1,
  });

  return (
    <div className="grid grid-cols-2 gap-6">
      <div>
        <div
          {...getRootProps()}
          className={`flex h-64 cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed ${
            isDragActive ? "border-blue-500 bg-blue-50" : "border-slate-300 bg-white"
          }`}
        >
          <input {...getInputProps()} />
          <p className="text-slate-600">Arrastra un PDF escaneado o haz clic</p>
          <p className="mt-1 text-xs text-slate-400">Clasificación automática en tiempo real</p>
        </div>
        {msg && <p className="mt-3 text-sm text-slate-600">{msg}</p>}
      </div>
      {doc && <ClasificacionPanel doc={doc} onSaved={setDoc} />}
    </div>
  );
}

function ClasificacionPanel({ doc, onSaved }: { doc: DocumentOut; onSaved: (d: DocumentOut) => void }) {
  const [tipo, setTipo] = useState(doc.tipo_codigo ?? "");
  const [area, setArea] = useState(doc.area_codigo ?? "");
  const [asunto, setAsunto] = useState(doc.asunto ?? "");
  const [anio, setAnio] = useState(doc.anio_documento ?? new Date().getFullYear());

  useEffect(() => {
    setTipo(doc.tipo_codigo ?? "");
    setArea(doc.area_codigo ?? "");
    setAsunto(doc.asunto ?? "");
    setAnio(doc.anio_documento ?? new Date().getFullYear());
  }, [doc]);

  const guardar = async () => {
    const updated = await classifyDocumento(doc.id, {
      tipo_codigo: tipo,
      area_codigo: area,
      asunto,
      anio_documento: anio,
    });
    onSaved(updated);
  };

  return (
    <div className="rounded-lg border bg-white p-4">
      <h2 className="mb-3 font-semibold">Clasificación propuesta</h2>
      <dl className="space-y-2 text-sm">
        <Field label="Estado" value={doc.estado} />
        <Field label="Correlativo" value={doc.correlativo ?? "—"} />
        <Field
          label="Confianza"
          value={doc.confianza != null ? `${Math.round(doc.confianza * 100)}%` : "—"}
        />
      </dl>
      <div className="mt-4 space-y-3">
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
          Año
          <input
            type="number"
            className="mt-1 w-full rounded border px-2 py-1"
            value={anio}
            onChange={(e) => setAnio(Number(e.target.value))}
          />
        </label>
        {doc.justificacion_llm && (
          <p className="rounded bg-slate-50 p-2 text-xs text-slate-500">{doc.justificacion_llm}</p>
        )}
        <button onClick={guardar} className="w-full rounded bg-blue-600 py-2 text-white hover:bg-blue-700">
          Confirmar y guardar
        </button>
      </div>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <dt className="text-slate-500">{label}</dt>
      <dd className="font-medium">{value}</dd>
    </div>
  );
}
