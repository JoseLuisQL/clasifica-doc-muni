"""Rutas de configuración: áreas, tipos, correlativo, LLM, anonimización, export/import YAML."""
from __future__ import annotations

import yaml
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from clasifica.api.deps import get_current_user, get_db
from clasifica.schemas import (
    AreaIn,
    AreaOut,
    CorrelativoConfig,
    LLMConfigOut,
    TipoIn,
    TipoOut,
)

router = APIRouter(prefix="/config", tags=["config"])


# ---- Áreas ----
@router.get("/areas", response_model=list[AreaOut])
async def listar_areas(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)) -> list[AreaOut]:
    from clasifica.db.models import Area

    rows = (await db.execute(select(Area).order_by(Area.orden))).scalars().all()
    return [AreaOut.model_validate(r) for r in rows]


@router.post("/areas", response_model=AreaOut, status_code=201)
async def crear_area(body: AreaIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)) -> AreaOut:
    from clasifica.db.models import Area

    if await db.get(Area, body.codigo):
        raise HTTPException(status_code=409, detail="El código de área ya existe")
    area = Area(**body.model_dump())
    db.add(area)
    await db.commit()
    await db.refresh(area)
    return AreaOut.model_validate(area)


@router.put("/areas/{codigo}", response_model=AreaOut)
async def actualizar_area(codigo: str, body: AreaIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)) -> AreaOut:
    from clasifica.db.models import Area

    area = await db.get(Area, codigo)
    if area is None:
        raise HTTPException(status_code=404, detail="Área no encontrada")
    for k, v in body.model_dump(exclude={"codigo"}).items():
        setattr(area, k, v)
    await db.commit()
    await db.refresh(area)
    return AreaOut.model_validate(area)


@router.delete("/areas/{codigo}", status_code=204)
async def desactivar_area(codigo: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)) -> None:
    from clasifica.db.models import Area

    area = await db.get(Area, codigo)
    if area:
        area.activa = False
        await db.commit()


# ---- Tipos ----
@router.get("/tipos", response_model=list[TipoOut])
async def listar_tipos(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)) -> list[TipoOut]:
    from clasifica.db.models import TipoDocumental

    rows = (await db.execute(select(TipoDocumental))).scalars().all()
    return [TipoOut.model_validate(r) for r in rows]


@router.post("/tipos", response_model=TipoOut, status_code=201)
async def crear_tipo(body: TipoIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)) -> TipoOut:
    from clasifica.db.models import TipoDocumental

    if await db.get(TipoDocumental, body.codigo):
        raise HTTPException(status_code=409, detail="El código de tipo ya existe")
    tipo = TipoDocumental(**body.model_dump())
    db.add(tipo)
    await db.commit()
    await db.refresh(tipo)
    return TipoOut.model_validate(tipo)


@router.put("/tipos/{codigo}", response_model=TipoOut)
async def actualizar_tipo(codigo: str, body: TipoIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)) -> TipoOut:
    from clasifica.db.models import TipoDocumental

    tipo = await db.get(TipoDocumental, codigo)
    if tipo is None:
        raise HTTPException(status_code=404, detail="Tipo no encontrado")
    for k, v in body.model_dump(exclude={"codigo"}).items():
        setattr(tipo, k, v)
    await db.commit()
    await db.refresh(tipo)
    return TipoOut.model_validate(tipo)


# ---- Correlativo ----
@router.get("/correlativo", response_model=CorrelativoConfig)
async def get_correlativo(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)) -> CorrelativoConfig:
    from clasifica.db.models import ConfiguracionCorrelativo

    cfg = await db.get(ConfiguracionCorrelativo, 1)
    return CorrelativoConfig(plantilla=cfg.plantilla if cfg else "{SEQ:04d}-{AREA}-{ANIO}-{TIPO}")


@router.put("/correlativo", response_model=CorrelativoConfig)
async def put_correlativo(body: CorrelativoConfig, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)) -> CorrelativoConfig:
    from clasifica.db.models import ConfiguracionCorrelativo

    cfg = await db.get(ConfiguracionCorrelativo, 1)
    if cfg is None:
        cfg = ConfiguracionCorrelativo(id=1, plantilla=body.plantilla)
        db.add(cfg)
    else:
        cfg.plantilla = body.plantilla
    await db.commit()
    return CorrelativoConfig(plantilla=body.plantilla)


# ---- LLM ----
@router.get("/llm", response_model=LLMConfigOut)
async def get_llm(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)) -> LLMConfigOut:
    from clasifica.db.models import ConfiguracionLLM

    cfg = await db.get(ConfiguracionLLM, 1)
    if cfg is None:
        raise HTTPException(status_code=404, detail="Config LLM no inicializada")
    return LLMConfigOut.model_validate(cfg)


@router.put("/llm", response_model=LLMConfigOut)
async def put_llm(body: dict, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)) -> LLMConfigOut:
    from clasifica.db.models import ConfiguracionLLM

    cfg = await db.get(ConfiguracionLLM, 1)
    if cfg is None:
        cfg = ConfiguracionLLM(id=1)
        db.add(cfg)
    editable = {"endpoint", "modelo", "temperatura", "max_tokens", "rate_limit_rpm", "timeout_segundos", "modelo_embeddings", "plantilla_system_prompt"}
    for k, v in body.items():
        if k in editable:
            setattr(cfg, k, v)
    await db.commit()
    await db.refresh(cfg)
    return LLMConfigOut.model_validate(cfg)


# ---- Anonimización ----
@router.get("/anonimizacion")
async def get_anon(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)) -> dict:
    from clasifica.db.models import ConfiguracionAnonimizacion

    cfg = await db.get(ConfiguracionAnonimizacion, 1)
    return {"patrones": cfg.patrones if cfg else [], "redactar_firmas": cfg.redactar_firmas if cfg else True}


@router.put("/anonimizacion")
async def put_anon(body: dict, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)) -> dict:
    from clasifica.db.models import ConfiguracionAnonimizacion

    cfg = await db.get(ConfiguracionAnonimizacion, 1)
    if cfg is None:
        cfg = ConfiguracionAnonimizacion(id=1)
        db.add(cfg)
    if "patrones" in body:
        cfg.patrones = body["patrones"]
    if "redactar_firmas" in body:
        cfg.redactar_firmas = body["redactar_firmas"]
    await db.commit()
    return {"patrones": cfg.patrones, "redactar_firmas": cfg.redactar_firmas}


# ---- Export/Import YAML ----
@router.get("/export")
async def export_config(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)) -> Response:
    from clasifica.db.models import Area, ConfiguracionCorrelativo, TipoDocumental

    areas = (await db.execute(select(Area))).scalars().all()
    tipos = (await db.execute(select(TipoDocumental))).scalars().all()
    corr = await db.get(ConfiguracionCorrelativo, 1)
    data = {
        "areas": [{"codigo": a.codigo, "nombre": a.nombre, "padre": a.padre_codigo, "tipo": a.tipo, "orden": a.orden} for a in areas],
        "tipos": [{"codigo": t.codigo, "nombre": t.nombre, "area_tipica": t.area_tipica_codigo, "descripcion": t.descripcion, "palabras_clave": t.palabras_clave} for t in tipos],
        "correlativo": {"plantilla": corr.plantilla if corr else ""},
    }
    return Response(content=yaml.safe_dump(data, allow_unicode=True), media_type="application/yaml")


@router.post("/import")
async def import_config(body: dict, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)) -> dict:
    """Importa áreas/tipos desde un dict (YAML parseado en el cliente o JSON)."""
    from clasifica.db.models import Area, TipoDocumental

    creados = {"areas": 0, "tipos": 0}
    for a in body.get("areas", []):
        if not await db.get(Area, a["codigo"]):
            db.add(Area(codigo=a["codigo"], nombre=a["nombre"], padre_codigo=a.get("padre"), tipo=a.get("tipo"), orden=a.get("orden", 0)))
            creados["areas"] += 1
    await db.flush()
    for t in body.get("tipos", []):
        if not await db.get(TipoDocumental, t["codigo"]):
            db.add(TipoDocumental(codigo=t["codigo"], nombre=t["nombre"], area_tipica_codigo=t.get("area_tipica"), descripcion=t.get("descripcion"), palabras_clave=t.get("palabras_clave", [])))
            creados["tipos"] += 1
    await db.commit()
    return creados
