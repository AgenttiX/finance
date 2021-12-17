import datetime
import enum
import typing as tp

import numpy as np
import pandas
import pyqtgraph as pg
import pytz
import yfinance as yf


@enum.unique
class Period(str, enum.Enum):
    P1D = "1d"
    P5D = "5d"
    P1MO = "1mo"
    P3MO = "3mo"
    P6MO = "6mo"
    P1Y = "1y"
    P2Y = "2y"
    P5Y = "5y"
    P10Y = "10y"
    YTD = "ytd"
    MAX = "max"


@enum.unique
class Interval(str, enum.Enum):
    I1M = "1m"
    I2M = "2m"
    I5M = "5m"
    I15M = "15m"
    I30M = "30m"
    I60M = "60m"
    I90M = "90m"
    I1H = "1h"
    I1D = "1d"
    I5D = "5d"
    I1WK = "1wk"
    I1MO = "1mo"
    I3MO = "3mo"


class Ticker:
    def __init__(self, code: str, name: str, color: tp.Union[str, tp.Tuple[int, int, int]] = None, data: yf.Ticker = None):
        self.code = code
        self.name = name
        self.color = color
        self.data = data if data else yf.Ticker(code)


class Tickers:
    def __init__(self,
                 tickers: tp.List[Ticker],
                 period: Period = None,
                 start: datetime.datetime = None,
                 end: datetime.datetime = None,
                 interval: Interval = None,
                 ):
        self.tickers = tickers
        # self.tickers_dict = {ticker.code: ticker for ticker in tickers}
        if (period is None) == (start is None and end is None):
            raise ValueError("Provide either a period or start and end times")
        self.period = period
        self.start = start
        self.end = end
        self.interval = interval
        self.data = None
        # self.update()

    def __len__(self):
        return self.tickers.__len__()

    def __getitem__(self, item):
        return self.tickers.__getitem__(item)

    def tickers_str(self) -> str:
        return " ".join([ticker.code for ticker in self.tickers])

    def update(self):
        kwargs = {}
        if self.period:
            kwargs["period"] = self.period
        self.data = yf.download(self.tickers_str(), period=self.period, interval=self.interval, group_by="ticker")


class StockWidget(pg.PlotWidget):
    def __init__(self, tickers: Tickers):
        date_axis = pg.DateAxisItem()
        # Fix daylight savings
        date_axis.utcOffset = - pytz.timezone("Europe/Helsinki").utcoffset(datetime.datetime.now()).total_seconds()
        super().__init__(axisItems={"bottom": date_axis})
        self.tickers = tickers
        self.addLegend()
        self.plots = []
        for ticker in self.tickers:
            kwargs = {}
            if ticker.color:
                kwargs["pen"] = ticker.color
            self.plots.append(self.plot(name=ticker.name, **kwargs))
        self.setLabel("bottom", "time")
        self.showGrid(x=True, y=True)
        self.update()

    @staticmethod
    def datetime64_to_int(value: tp.Union[np.ndarray, pandas.Timestamp]):
        return value.astype(np.int_)//(10**9)

    def update(self):
        self.tickers.update()
        today_midnight = datetime.datetime.combine(
            datetime.date.today(), datetime.time(hour=0), tzinfo=pytz.timezone("Europe/Helsinki"))
        today_morning = datetime.datetime.combine(
            datetime.date.today(), datetime.time(hour=9), tzinfo=pytz.timezone("Europe/Helsinki"))
        today_evening = datetime.datetime.combine(
            datetime.date.today(), datetime.time(hour=22), tzinfo=pytz.timezone("Europe/Helsinki"))
        y_min = 0.95
        y_max = 1.05
        for plot, ticker in zip(self.plots, self.tickers):
            data = self.tickers.data[ticker.code].dropna()
            close = data["Close"].values
            today_close = data[np.all([today_morning <= data.index, data.index <= today_evening], axis=0)]["Close"].values
            last_close = data[data.index < today_midnight]["Close"][-1]
            y_values = close / last_close
            if today_close.size:
                y_min = min(y_min, today_close.min() / last_close)
                y_max = max(y_max, today_close.max() / last_close)
            plot.setData(self.datetime64_to_int(data.index.values), y_values)
        self.setXRange(today_morning.timestamp(), today_evening.timestamp())
        self.setYRange(y_min, y_max)


def main():
    omxh25 = Ticker(code="^OMXH25", name="OMXH25", color=(254, 128, 7))
    fortum = Ticker(code="FORTUM.HE", name="Fortum", color=(90, 195, 125))
    nokia = Ticker(code="NOKIA.HE", name="Nokia", color=(18, 65, 145))
    sampo = Ticker(code="SAMPO.HE", name="Sampo", color=(19, 24, 40))
    wartsila = Ticker(code="WRT1V.HE", name="Wärtsilä", color=(7, 103, 148))

    nasdaq = Ticker(code="^IXIC", name="NASDAQ", color=(127, 0, 255))
    nvidia = Ticker(code="NVDA", name="Nvidia", color=(118, 185, 0))
    amd = Ticker(code="AMD", name="AMD", color=(224, 0, 49))
    tesla = Ticker(code="TSLA", name="Tesla", color=(232, 33, 39))

    tickers = Tickers(
        [
            omxh25, fortum, nokia, sampo, wartsila,
            nasdaq, nvidia, amd, tesla
        ],
        period=Period.P5D, interval=Interval.I1M)

    app = pg.mkQApp()
    pg.setConfigOptions(background="w", foreground="k", antialias=True)
    win = StockWidget(tickers)
    timer = pg.QtCore.QTimer()
    timer.timeout.connect(win.update)
    timer.start(60*1000)

    win.show()
    app.exec_()


main()
