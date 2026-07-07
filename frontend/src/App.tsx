import { useState } from "react";
import { useAuthStore } from "@/stores/auth";
import { LoginPage } from "@/features/auth/LoginPage";
import { UploadPage } from "@/features/upload/UploadPage";
import { MigrationPage } from "@/features/migration/MigrationPage";
import { ReviewPage } from "@/features/review/ReviewPage";
import { ExplorerPage } from "@/features/explorer/ExplorerPage";
import { ConfigPage } from "@/features/config/ConfigPage";

type Tab = "upload" | "migration" | "review" | "explorer" | "config";

const TABS: { id: Tab; label: string }[] = [
  { id: "upload", label: "Carga individual" },
  { id: "migration", label: "Migración masiva" },
  { id: "review", label: "Bandeja de revisión" },
  { id: "explorer", label: "Explorar / Buscar" },
  { id: "config", label: "Configuración" },
];

export function App() {
  const { accessToken, logout } = useAuthStore();
  const [tab, setTab] = useState<Tab>("upload");

  if (!accessToken) return <LoginPage />;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="flex items-center justify-between border-b bg-white px-6 py-3 shadow-sm">
        <h1 className="text-lg font-semibold">ClasificaDocMuni</h1>
        <nav className="flex gap-1">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`rounded px-3 py-1.5 text-sm ${
                tab === t.id ? "bg-blue-600 text-white" : "hover:bg-slate-100"
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
        <button onClick={logout} className="text-sm text-slate-500 hover:text-slate-800">
          Salir
        </button>
      </header>
      <main className="mx-auto max-w-6xl p-6">
        {tab === "upload" && <UploadPage />}
        {tab === "migration" && <MigrationPage />}
        {tab === "review" && <ReviewPage />}
        {tab === "explorer" && <ExplorerPage />}
        {tab === "config" && <ConfigPage />}
      </main>
    </div>
  );
}
