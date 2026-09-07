import yfinance as yf

def buscar_ativo(ticker):
    ativo = yf.Ticker(ticker)
    info = ativo.info

    if not info or info.get('quoteType') is None:
        raise ValueError('Ativo não encontrado')
    
    return {
        "ticker": ticker,
        "nome": info.get("longName"),
        "preco": info.get("currentPrice"),
        "variacao_dia": info.get("regularMarketChangePercent"), 
        "abertura": info.get("open"),
        "maxima": info.get("dayHigh"),
        "minima": info.get("dayLow"),
        "volume": info.get("volume"),
        "market_cap": info.get("marketCap"),
        "setor": info.get("sector"),
        "industria": info.get("industry"),
        "dividend_yield": info.get("dividendYield"),
        "pe": info.get("trailingPE"),
        "eps": info.get("trailingEps"),
        "moeda": info.get("currency"),
    }
