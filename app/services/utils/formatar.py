def formatar_ticker(ticker: str):
    ticker = ticker.upper()

    if '.' in ticker:
        return ticker

    return f"{ticker}.SA"