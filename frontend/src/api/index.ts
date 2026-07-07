import axios from "axios";
import { useAuthStore } from "@/stores/auth";

export const api = axios.create({ baseURL: "/api/v1" });

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  async (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
    }
    return Promise.reject(error);
  },
);

export interface DocumentOut {
  id: string;
  hash_sha256: string;
  correlativo: string | null;
  estado: string;
  tipo_codigo: string | null;
  area_codigo: string | null;
  asunto: string | null;
  anio_documento: number | null;
  confianza: number | null;
  justificacion_llm: string | null;
  num_paginas: number | null;
  tamano_bytes: number;
  origen: string;
  ruta_clasificada: string | null;
  cargado_en: string;
  procesado_en: string | null;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export const login = (username: string, password: string) =>
  api.post("/auth/login", { username, password }).then((r) => r.data);

export const uploadDocumento = (file: File) => {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("origen", "interactivo");
  return api.post<DocumentOut>("/documents", fd).then((r) => r.data);
};

export const getDocumento = (id: string) =>
  api.get<DocumentOut>(`/documents/${id}`).then((r) => r.data);

export const getEventos = (id: string) =>
  api.get(`/documents/${id}/events`).then((r) => r.data);

export const classifyDocumento = (id: string, body: Record<string, unknown>) =>
  api.post<DocumentOut>(`/documents/${id}/classify`, body).then((r) => r.data);

export const listDocumentos = (params: Record<string, unknown>) =>
  api.get<Paginated<DocumentOut>>("/documents", { params }).then((r) => r.data);

export const bandejaRevision = () =>
  api.get<Paginated<DocumentOut>>("/documents/review").then((r) => r.data);

export const searchDocumentos = (params: Record<string, unknown>) =>
  api.get<Paginated<DocumentOut>>("/documents/search", { params }).then((r) => r.data);

export const similares = (id: string) =>
  api.get(`/documents/${id}/similar`).then((r) => r.data);

export const suggest = (q: string) =>
  api.get("/search/suggest", { params: { q } }).then((r) => r.data);

export const crearMigracion = (ruta_origen: string) =>
  api.post("/migration/jobs", { ruta_origen }).then((r) => r.data);

export const listMigraciones = () => api.get("/migration/jobs").then((r) => r.data);
export const pausarJob = (id: string) => api.post(`/migration/jobs/${id}/pause`);
export const reanudarJob = (id: string) => api.post(`/migration/jobs/${id}/resume`);

export const getAreas = () => api.get("/config/areas").then((r) => r.data);
export const getTipos = () => api.get("/config/tipos").then((r) => r.data);
export const getStats = () => api.get("/reports/stats").then((r) => r.data);
