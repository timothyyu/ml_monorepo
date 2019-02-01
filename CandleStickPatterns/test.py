import candlestickpatterns
import quandl
from datetime import datetime
import pandas as pd

df = pd.read_json('test_data.json')
df = df.sort_values(by=['Date'])

t=candlestickpatterns.pattern_generate(df)

print(t.head())
