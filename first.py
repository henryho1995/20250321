import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class Trade:
    entry_price: float
    exit_price: float
    result: str
    position_size: int
    entry_time: datetime
    exit_time: datetime


class ORBStrategy:
    def __init__(
        self, symbol: str, initial_capital: float = 25000, risk_percent: float = 0.01
    ):
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.risk_percent = risk_percent
        self.capital = initial_capital
        self.position = 0
        self.trades: List[Trade] = []

    def fetch_data(self, days: int = 60, interval: str = "5m") -> pd.DataFrame:
        """獲取市場數據"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        ticker = yf.Ticker(self.symbol)
        return ticker.history(start=start_date, end=end_date, interval=interval)[
            ["Open", "High", "Low", "Close"]
        ]

    def calculate_position_size(self, entry_price: float, stop_loss: float) -> int:
        """計算倉位大小"""
        risk = abs(entry_price - stop_loss)
        return int((self.capital * self.risk_percent) / risk)

    def process_trade(
        self,
        current_candle: pd.Series,
        entry_price: float,
        stop_loss: float,
        profit_target: float,
        position_size: int,
        entry_time: datetime,
    ) -> bool:
        """處理交易邏輯"""
        if self.position == 1:  # 多頭
            if current_candle["Low"] <= stop_loss:
                self._close_trade(
                    stop_loss,
                    "Loss",
                    position_size,
                    entry_price,
                    entry_time,
                    current_candle.name,
                )
                return True
            elif current_candle["High"] >= profit_target:
                self._close_trade(
                    profit_target,
                    "Profit",
                    position_size,
                    entry_price,
                    entry_time,
                    current_candle.name,
                )
                return True
        elif self.position == -1:  # 空頭
            if current_candle["High"] >= stop_loss:
                self._close_trade(
                    stop_loss,
                    "Loss",
                    position_size,
                    entry_price,
                    entry_time,
                    current_candle.name,
                )
                return True
            elif current_candle["Low"] <= profit_target:
                self._close_trade(
                    profit_target,
                    "Profit",
                    position_size,
                    entry_price,
                    entry_time,
                    current_candle.name,
                )
                return True
        return False

    def _close_trade(
        self,
        exit_price: float,
        result: str,
        position_size: int,
        entry_price: float,
        entry_time: datetime,
        exit_time: datetime,
    ):
        """關閉交易並記錄結果"""
        trade = Trade(
            entry_price=entry_price,
            exit_price=exit_price,
            result=result,
            position_size=position_size,
            entry_time=entry_time,
            exit_time=exit_time,
        )
        self.trades.append(trade)

        pnl = (exit_price - entry_price) * position_size * self.position
        self.capital += pnl
        self.position = 0

    def backtest(self, data: pd.DataFrame) -> Tuple[List[Trade], float]:
        """執行回測"""
        for i in range(1, len(data)):
            current_candle = data.iloc[i]
            previous_candle = data.iloc[i - 1]

            # 檢查是否為交易時段開始（09:35）
            if current_candle.name.time() == pd.Timestamp("09:35:00").time():
                opening_range_high = previous_candle["High"]
                opening_range_low = previous_candle["Low"]

                # 開盤區間為多頭
                if previous_candle["Close"] > previous_candle["Open"]:
                    entry_price = current_candle["Open"]
                    stop_loss = opening_range_low
                    risk = entry_price - stop_loss
                    profit_target = entry_price + (risk * 10)
                    position_size = self.calculate_position_size(entry_price, stop_loss)
                    self.position = 1

                # 開盤區間為空頭
                elif previous_candle["Close"] < previous_candle["Open"]:
                    entry_price = current_candle["Open"]
                    stop_loss = opening_range_high
                    risk = stop_loss - entry_price
                    profit_target = entry_price - (risk * 10)
                    position_size = self.calculate_position_size(entry_price, stop_loss)
                    self.position = -1

                if self.position != 0:
                    entry_time = current_candle.name

            # 檢查止損或獲利目標
            if self.position != 0:
                self.process_trade(
                    current_candle,
                    entry_price,
                    stop_loss,
                    profit_target,
                    position_size,
                    entry_time,
                )

        return self.trades, self.capital

