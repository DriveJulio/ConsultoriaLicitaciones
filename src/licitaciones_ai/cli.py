"""Línea de comandos: python -m licitaciones_ai <comando>."""
from __future__ import annotations

import argparse
from datetime import date


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="licitaciones", description="IA agéntica para licitaciones en Argentina")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("boletin", help="Revisa el Boletín Oficial del día (o --fecha AAAA-MM-DD)")
    b.add_argument("--fecha", type=date.fromisoformat)

    sub.add_parser("expedientes", help="Controla novedades en los expedientes seguidos")

    c = sub.add_parser("consejo", help="Diálogo Especialista ↔ Asesor (ambos Fable)")
    c.add_argument("--rondas", type=int, default=2)
    c.add_argument("--tema")

    sub.add_parser("verificar-marco", help="Verifica la vigencia del marco normativo base")

    q = sub.add_parser("preguntar", help="Consulta directa al Especialista")
    q.add_argument("pregunta")

    a = p.parse_args(argv)

    if a.cmd == "boletin":
        from .monitors import boletin

        print(boletin.ejecutar(a.fecha))
    elif a.cmd == "expedientes":
        from .monitors import expedientes

        print(expedientes.ejecutar())
    elif a.cmd == "consejo":
        from .agents import consejo

        print(consejo.sesionar(a.rondas, a.tema))
    elif a.cmd == "verificar-marco":
        from . import state
        from .agents.orquestador import especialista

        r = especialista().enviar(
            "Leé knowledge/marco_normativo.md. Para cada norma marcada [A VERIFICAR] o cuya vigencia pueda haber "
            "cambiado, delegá a analistas (usar_web=true, en paralelo) la verificación contra InfoLEG/Boletín "
            "Oficial: vigencia, modificaciones posteriores y texto actualizado. Devolvé una tabla con norma, "
            "estado verificado, modificaciones y fuente, y registrá una propuesta con los cambios al archivo."
        )
        print(state.guardar_reporte("verificacion-marco", f"# Verificación del marco normativo\n\n{r}"))
    elif a.cmd == "preguntar":
        from .agents.orquestador import especialista

        print(especialista().enviar(a.pregunta))


if __name__ == "__main__":
    main()
