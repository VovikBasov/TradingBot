#!/usr/bin/env python3
import pandas as pd
import asyncio
from datetime import datetime, timedelta
from tinkoff.invest import AsyncClient, CandleInterval
from dotenv import load_dotenv
import os
load_dotenv()

async def main():
    async with AsyncClient(os.getenv('INVEST_TOKEN')) as client:
        # Запрашиваем последние 5 часовых свечей для GAZP
        candles = []
        async for candle in client.get_all_candles(
            figi="BBG004730RP0",
            from_=datetime.utcnow() - timedelta(hours=10),
            to=datetime.utcnow(),
            interval=CandleInterval.CANDLE_INTERVAL_HOUR
        ):
            candles.append({
                'time': candle.time,
                'open': candle.open.units + candle.open.nano / 1e9,
                'high': candle.high.units + candle.high.nano / 1e9,
                'low': candle.low.units + candle.low.nano / 1e9,
                'close': candle.close.units + candle.close.nano / 1e9,
                'volume': candle.volume
            })
        df_api = pd.DataFrame(candles).set_index('time').sort_index()
        print("Данные из Tinkoff Invest API (последние 5 свечей):")
        print(df_api.tail().to_string())
        print(f"\nПример свечи для ручной проверки:")
        print(f"Время: {df_api.index[-1]}")
        print(f"O:{df_api.iloc[-1]['open']:.2f} H:{df_api.iloc[-1]['high']:.2f} L:{df_api.iloc[-1]['low']:.2f} C:{df_api.iloc[-1]['close']:.2f}")

if __name__ == "__main__":
    asyncio.run(main())
