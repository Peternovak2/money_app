"""Estado previsto da sessão regular de ações; não é um feed operacional em tempo real."""
import json
from datetime import date, datetime, time, timezone
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


CAMINHO_CALENDARIO = Path(__file__).resolve().parents[1] / 'data' / 'b3_2026.json'
FUSO_B3 = 'America/Sao_Paulo'
ROTULOS = {'aberto': 'Aberto', 'fechado': 'Fechado', 'indisponivel': 'Status indisponível'}


@lru_cache(maxsize=1)
def _carregar_calendario():
    dados = json.loads(CAMINHO_CALENDARIO.read_text(encoding='utf-8'))
    if (not isinstance(dados, dict)
            or not all(isinstance(dados.get(chave), list) and dados[chave] for chave in ('fontes', 'feriados', 'grades'))
            or not isinstance(dados.get('especiais'), dict)):
        raise ValueError('Calendário incompleto')
    ano = dados['ano']
    if type(ano) is not int or not dados['fontes'] or not dados['feriados'] or not dados['grades']:
        raise ValueError('Calendário incompleto')
    feriados = {date.fromisoformat(valor) for valor in dados['feriados']}
    if any(dia.year != ano for dia in feriados):
        raise ValueError('Feriado fora do ano do calendário')
    grades = []
    for grade in dados['grades']:
        inicio, fim = date.fromisoformat(grade['inicio']), date.fromisoformat(grade['fim'])
        abertura, fechamento = time.fromisoformat(grade['abertura']), time.fromisoformat(grade['fechamento'])
        if inicio.year != ano or fim.year != ano or inicio > fim or abertura >= fechamento:
            raise ValueError('Grade inválida')
        grades.append((inicio, fim, abertura, fechamento))
    especiais = {}
    for valor, grade in dados['especiais'].items():
        dia = date.fromisoformat(valor)
        abertura, fechamento = time.fromisoformat(grade['abertura']), time.fromisoformat(grade['fechamento'])
        if dia.year != ano or abertura >= fechamento:
            raise ValueError('Horário especial inválido')
        especiais[dia] = (abertura, fechamento)
    return ano, feriados, grades, especiais


def obter_sessao_b3(agora=None):
    agora = agora if agora is not None else datetime.now(timezone.utc)
    resultado = dict(status='indisponivel', rotulo=ROTULOS['indisponivel'],
                     escopo='sessao_regular_acoes_b3', timezone=FUSO_B3,
                     referencia=agora.isoformat(), atualizar_em=60,
                     detalhe='Calendário ou grade oficial indisponível para esta data.')
    try:
        if agora.tzinfo is None or agora.utcoffset() is None:
            return resultado
        local = agora.astimezone(ZoneInfo(FUSO_B3))
        ano, feriados, grades, especiais = _carregar_calendario()
        dia = local.date()
        if dia.year != ano:
            return resultado
        horario = especiais.get(dia)
        if horario is None:
            horario = next(((abertura, fechamento) for inicio, fim, abertura, fechamento in grades
                            if inicio <= dia <= fim), None)
        if dia.weekday() >= 5 or dia in feriados:
            estado, intervalo = 'fechado', 300
        elif horario is None:
            return resultado
        else:
            inicio = datetime.combine(dia, horario[0], local.tzinfo)
            fim = datetime.combine(dia, horario[1], local.tzinfo)
            estado = 'aberto' if inicio <= local < fim else 'fechado'
            limite = 60 if estado == 'aberto' else 300
            proxima = inicio if local < inicio else fim if local < fim else None
            intervalo = min(limite, max(1, int((proxima - local).total_seconds()))) if proxima else limite
        resultado.update(status=estado, rotulo=ROTULOS[estado], atualizar_em=intervalo,
                         referencia=local.isoformat(),
                         detalhe='Sessão regular prevista pelo calendário oficial da B3. '
                                 'Não confirma interrupções, leilões ou after-market em tempo real.')
    except (OSError, ValueError, TypeError, KeyError, ZoneInfoNotFoundError):
        # Sem um calendário válido, não se presume que o mercado está fechado.
        pass
    return resultado
