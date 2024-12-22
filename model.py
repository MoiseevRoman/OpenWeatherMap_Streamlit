from datetime import datetime

import pandas as pd
import aiohttp
from sklearn.linear_model import LinearRegression

from utils import month_to_season


def heavy_func(city, df):
    new_df = df[df['city'] == city].copy()
    new_df['timestamp'] = pd.to_datetime(new_df['timestamp'])

    new_df.set_index('timestamp', inplace=True)
    new_df['MA'] = new_df['temperature'].rolling(window='30D', min_periods=1).mean()
    new_df['std'] = new_df['temperature'].rolling(window='30D', min_periods=1).std()
    new_df['anomaly'] = (
        (new_df['temperature'] > new_df['MA'] + 2 * new_df['std']) |
        (new_df['temperature'] < new_df['MA'] - 2 * new_df['std'])
    )

    season_df = df[df['city'] == city].copy()
    season_profile = season_df.groupby('season')['temperature'].agg(average='mean', std='std').reset_index()

    trend_df = df[df['city'] == city].copy()
    trend_df['timestamp'] = pd.to_datetime(trend_df['timestamp'])
    timestamps_numeric = ((trend_df['timestamp'] - trend_df['timestamp'].min()).dt.total_seconds()/60/60/24).values.reshape(-1, 1)
    temperatures = trend_df['temperature'].values.reshape(-1, 1)

    model = LinearRegression()
    model.fit(timestamps_numeric, temperatures)

    if model.coef_[0, 0] > 0:
        trend = 'Positive'
    else:
        trend = 'Negative'

    avg_temp = new_df['temperature'].mean()
    min_temp = new_df['temperature'].min()
    max_temp = new_df['temperature'].max()
    anomaly_df = df[df['city'] == city].copy()

    anomaly_df = anomaly_df.merge(season_profile, on='season', how='left')
    anomaly_df['is_anomaly'] = (
        (anomaly_df['temperature'] > anomaly_df['average'] + 2 * anomaly_df['std']) |
        (anomaly_df['temperature'] < anomaly_df['average'] - 2 * anomaly_df['std'])
    )

    anomaly_points = anomaly_df[anomaly_df['is_anomaly'] ==1]
    return avg_temp, min_temp, max_temp, new_df, season_profile, trend, anomaly_points


async def is_normal_async(city, df, api_key):
    async with aiohttp.ClientSession() as session:
        url = f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}'
        async with session.get(url) as response:
            data = await response.json()
            if response.status == 401:
                return None, data

            t = data['main']['temp'] - 273.15

            _, _, _, _, season_profile, _, _ = heavy_func(city, df)
            season = month_to_season[datetime.now().month]
            avg = season_profile[season_profile['season'] == season]['average'].values[0]
            std = season_profile[season_profile['season'] == season]['std'].values[0]

            if (t > avg + 2 * std) | (t < avg - 2 * std):
                return t, 'Anomaly temp'
            else:
                return t, 'Normal temp'