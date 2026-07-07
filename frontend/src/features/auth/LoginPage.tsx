import { useState } from "react";
import { login } from "@/api";
import { useAuthStore } from "@/stores/auth";

export function LoginPage() {
  const setTokens = useAuthStore((s) => s.setTokens);
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      const data = await login(username, password);
      setTokens(data.access_token, data.refresh_token);
    } catch {
      setError("Credenciales inválidas");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100">
      <form onSubmit={submit} className="w-80 space-y-4 rounded-lg bg-white p-8 shadow">
        <h1 className="text-center text-xl font-semibold">ClasificaDocMuni</h1>
        <p className="text-center text-sm text-slate-500">Clasificación documental municipal</p>
        <input
          className="w-full rounded border px-3 py-2"
          placeholder="Usuario"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <input
          className="w-full rounded border px-3 py-2"
          type="password"
          placeholder="Contraseña"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button className="w-full rounded bg-blue-600 py-2 text-white hover:bg-blue-700">
          Ingresar
        </button>
      </form>
    </div>
  );
}
