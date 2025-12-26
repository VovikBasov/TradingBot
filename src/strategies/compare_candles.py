#!/usr/bin/env python3
import pandas as pd
import asyncio
from datetime import datetime
from tinkoff.invest import AsyncClient, CandleInterval
from dotenv import load_dotenv
load_dotenv()
import os

async def get_tinkoff_candles():
    async with AsyncClient(os.getenv('INVEST_TOKEN')) as client:
        candles = []
        async for candle in client.get_all_candles(
            figi="BBG004730RP0",
            from_=datetime(2024, 1, 1),
            to=datetime(2025, 1, 1),
            interval=CandleInterval.CANDLE_INTERVAL_HOUR
        ):
            candles.append([
                candle.time.isoformat(),
                candle.open.units + candle.open.nano / 1e9,
                candle.high.units + candle.high.nano / 1e9,
                candle.low.units + candle.low.nano / 1e9,
                candle.close.units + candle.close.nano / 1e9,
                candle.volume
            ])
        df = pd.DataFrame(candles, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        df.to_csv('tinkoff_candles_2024.csv', index=False)
        print(f"Сохранено {len(df)} свечей из Tinkoff API")
        return df

if __name__ == "__main__":
    asyncio.run(get_tinkoff_candles())
