"""Consejo: diálogo entre los dos orquestadores Fable (Especialista y Asesor).

El Asesor audita y propone; el Especialista responde, acepta o rechaza con fundamento y
registra decisiones. Las propuestas quedan para aprobación humana (no se auto-aplican).
"""
from __future__ import annotations

from .. import config, state
from .orquestador import asesor, especialista, resumen_registros


def _briefing() -> str:
    regs = state.leer_jsonl(state.REGISTRO)[-60:]
    ultimos = "\n".join(f"- {r['fecha']} {r['tipo']} [{r['prioridad']}] {r['titulo']}" for r in regs) or "(vacío)"
    return (
        f"Fecha: {config.ahora():%Y-%m-%d %H:%M} (hora Argentina).\n\n"
        "Últimos registros del sistema (decisiones, alertas, propuestas):\n"
        f"{ultimos}\n\n"
        "Archivos útiles: knowledge/marco_normativo.md, knowledge/novedades_normativas.md, "
        "config/expedientes.yaml, config/normativa.yaml, data/ (estado), reports/ (reportes)."
    )


def sesionar(rondas: int = 2, tema: str | None = None) -> str:
    esp, ase = especialista(), asesor()
    agenda = tema or (
        "Revisión periódica: (1) ¿hubo cambios normativos o novedades en expedientes que requieran acción? "
        "(2) ¿qué le falta a este sistema para ser la mejor IA agéntica de licitaciones de Argentina? "
        "(3) prioridades para la próxima semana."
    )

    apertura = esp.enviar(
        f"{_briefing()}\n\nAgenda del consejo: {agenda}\n\n"
        "Prepará tu informe de situación para el Asesor: estado, riesgos y lo que vos propondrías. "
        "Delegá a analistas lo que necesites verificar."
    )
    transcripcion = [f"### Especialista — apertura\n\n{apertura}"]
    ultimo = apertura

    for i in range(1, rondas + 1):
        critica = ase.enviar(
            f"Informe del Especialista (ronda {i}):\n\n{ultimo}\n\n"
            "Auditá su criterio legal y proponé mejoras concretas al sistema. Registrá tus propuestas."
        )
        transcripcion.append(f"### Asesor — ronda {i}\n\n{critica}")
        ultimo = esp.enviar(
            f"Respuesta del Asesor (ronda {i}):\n\n{critica}\n\n"
            "Respondé punto por punto: aceptás, rechazás o pedís más información, con fundamento. "
            "Registrá las decisiones adoptadas y las alertas que correspondan."
            + (" Cerrá con un resumen ejecutivo y un plan priorizado." if i == rondas else "")
        )
        transcripcion.append(f"### Especialista — ronda {i}\n\n{ultimo}")

    regs = esp.registros + ase.registros
    reporte = (
        f"# Consejo Especialista ↔ Asesor — {config.ahora():%Y-%m-%d %H:%M}\n\n"
        f"**Agenda:** {agenda}\n\n## Registros\n\n{resumen_registros(regs)}\n\n"
        "## Transcripción\n\n" + "\n\n".join(transcripcion)
    )
    path = state.guardar_reporte("consejo", reporte)
    return str(path)
