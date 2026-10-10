import re
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests


AGENCIA_BRASIL_RSS_URL = 'https://agenciabrasil.ebc.com.br/rss/economia/feed.xml'
AGENCIA_BRASIL_TIMEOUT = 4
QUANTIDADE_MAXIMA_NOTICIAS = 3
TAMANHO_MAXIMO_RESUMO = 320

PARAMETROS_RASTREAMENTO = {
    'fbclid',
    'gclid',
    'mc_cid',
    'mc_eid',
}


class _ExtratorTexto(HTMLParser):
    TAGS_IGNORADAS = {'script', 'style'}
    TAGS_DE_BLOCO = {
        'article', 'br', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'header', 'li', 'main', 'p', 'section', 'tr',
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._nivel_ignorado = 0
        self._partes = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()

        if tag in self.TAGS_IGNORADAS:
            self._nivel_ignorado += 1
        elif self._nivel_ignorado == 0 and tag in self.TAGS_DE_BLOCO:
            self._partes.append(' ')

    def handle_endtag(self, tag):
        tag = tag.lower()

        if tag in self.TAGS_IGNORADAS and self._nivel_ignorado > 0:
            self._nivel_ignorado -= 1
        elif self._nivel_ignorado == 0 and tag in self.TAGS_DE_BLOCO:
            self._partes.append(' ')

    def handle_data(self, data):
        if self._nivel_ignorado == 0:
            self._partes.append(data)

    def texto(self):
        return ' '.join(''.join(self._partes).split())


def _texto(elemento):
    if elemento is None or elemento.text is None:
        return None

    valor = unescape(elemento.text).strip()
    return valor or None


def _elementos_por_nome(item, nome):
    return [
        elemento
        for elemento in list(item)
        if elemento.tag.rsplit('}', 1)[-1] == nome
    ]


def _primeiro_texto(item, nome):
    elementos = _elementos_por_nome(item, nome)
    return _texto(elementos[0]) if elementos else None


def _validar_url(valor):
    if not isinstance(valor, str):
        return None

    url = unescape(valor).strip()

    try:
        partes = urlsplit(url)
    except ValueError:
        return None

    if partes.scheme.lower() not in {'http', 'https'} or not partes.netloc:
        return None

    return url


def _normalizar_url(url):
    partes = urlsplit(url)
    parametros = [
        (chave, valor)
        for chave, valor in parse_qsl(partes.query, keep_blank_values=True)
        if not chave.lower().startswith('utm_')
        and chave.lower() not in PARAMETROS_RASTREAMENTO
    ]
    caminho = partes.path.rstrip('/') or '/'

    return urlunsplit((
        partes.scheme.lower(),
        partes.netloc.lower(),
        caminho,
        urlencode(parametros, doseq=True),
        '',
    ))


def _normalizar_titulo(titulo):
    sem_acentos = ''.join(
        caractere
        for caractere in unicodedata.normalize('NFKD', titulo)
        if not unicodedata.combining(caractere)
    )
    return re.sub(r'\s+', ' ', sem_acentos).strip().casefold()


def _converter_data(valor):
    if not valor:
        return None

    try:
        publicado_em = parsedate_to_datetime(valor)
    except (TypeError, ValueError, OverflowError):
        return None

    if not isinstance(publicado_em, datetime) or publicado_em.tzinfo is None:
        return None

    return publicado_em


def _limpar_resumo(description):
    if not description:
        return None

    extrator = _ExtratorTexto()

    try:
        extrator.feed(description)
        extrator.close()
    except (TypeError, ValueError):
        return None

    resumo = extrator.texto()
    if not resumo:
        return None

    if len(resumo) <= TAMANHO_MAXIMO_RESUMO:
        return resumo

    resumo_reduzido = resumo[:TAMANHO_MAXIMO_RESUMO + 1].rsplit(' ', 1)[0]
    return f'{resumo_reduzido}…'


def _normalizar_item(item):
    titulo = _primeiro_texto(item, 'title')
    url = _validar_url(_primeiro_texto(item, 'link'))
    publicado_em = _converter_data(_primeiro_texto(item, 'pubDate'))

    if not titulo or not url or publicado_em is None:
        return None

    categorias = []
    for elemento in _elementos_por_nome(item, 'category'):
        categoria = _texto(elemento)
        if categoria and categoria not in categorias:
            categorias.append(categoria)

    return {
        'id_externo': _primeiro_texto(item, 'guid'),
        'titulo': titulo,
        'fonte': 'Agência Brasil',
        'autor': _primeiro_texto(item, 'creator'),
        'url': url,
        'imagem': _validar_url(_primeiro_texto(item, 'imagem-destaque')),
        'publicado_em': publicado_em,
        'resumo': _limpar_resumo(_primeiro_texto(item, 'description')),
        'categorias': categorias,
        'origem': 'agencia_brasil_rss',
    }


def _remover_duplicatas(noticias):
    resultado = []
    urls_vistas = set()
    ids_vistos = set()
    titulos_vistos = set()

    for noticia in noticias:
        url_normalizada = _normalizar_url(noticia['url'])
        id_externo = noticia['id_externo']
        chave_titulo = (
            _normalizar_titulo(noticia['titulo']),
            noticia['fonte'].casefold(),
            noticia['publicado_em'].isoformat(),
        )

        if (
            url_normalizada in urls_vistas
            or (id_externo and id_externo in ids_vistos)
            or chave_titulo in titulos_vistos
        ):
            continue

        urls_vistas.add(url_normalizada)
        if id_externo:
            ids_vistos.add(id_externo)
        titulos_vistos.add(chave_titulo)
        resultado.append(noticia)

    return resultado


def buscar_noticias_home():
    """Busca e normaliza até três notícias de Economia da Agência Brasil."""
    try:
        resposta = requests.get(
            AGENCIA_BRASIL_RSS_URL,
            headers={
                'Accept': 'application/rss+xml, application/xml;q=0.9',
                'User-Agent': 'Money-App/1.0',
            },
            timeout=AGENCIA_BRASIL_TIMEOUT,
        )
        resposta.raise_for_status()
        raiz = ET.fromstring(resposta.content)

        noticias = []
        for item in raiz.findall('.//item'):
            noticia = _normalizar_item(item)
            if noticia is not None:
                noticias.append(noticia)

        noticias.sort(key=lambda noticia: noticia['publicado_em'], reverse=True)
        noticias = _remover_duplicatas(noticias)
        return noticias[:QUANTIDADE_MAXIMA_NOTICIAS]
    except Exception:
        return []
