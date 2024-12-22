import asyncio

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from model import heavy_func, is_normal_async


async def process_main_page():
    await show_main_page()


async def show_main_page():

    st.title("Анализ температуры и текущая погода")

    uploaded_file = st.file_uploader(
        "Загрузите файл с историческими данными (CSV):", type=["csv"]
    )

    data = None
    if uploaded_file:
        data = load_data(uploaded_file)

    if data is not None:
        cities = data["city"].unique()
        selected_city = st.selectbox("Выберите город:", cities)

        if selected_city:
            (
                avg_temp,
                min_temp,
                max_temp,
                city_data,
                season_profile,
                trend,
                anomaly_points,
            ) = heavy_func(selected_city, data)

            st.subheader("Описательная статистика")
            st.write(f"Средняя температура: {avg_temp:.2f} °C")
            st.write(f"Минимальная температура: {min_temp:.2f} °C")
            st.write(f"Максимальная температура: {max_temp:.2f} °C")

            st.subheader("Временной ряд температур с аномалиями")
            plot_temperature_series_with_anomalies(
                city_data, city_data["MA"], anomaly_points
            )

            st.subheader("Сезонные профили")
            plot_seasonal_profile(season_profile)

            api_key = st.text_input("Введите API-ключ OpenWeatherMap:", type="password")

            if api_key:
                current_temp, temp_status = await is_normal_async(
                    selected_city, data, api_key
                )
                if temp_status == "Anomaly temp":
                    st.warning(
                        f"Текущая температура {current_temp:.2f} °C является аномальной для сезона."
                    )
                elif temp_status == "Normal temp":
                    st.success(
                        f"Текущая температура {current_temp:.2f} °C находится в пределах нормы для сезона."
                    )
                else:
                    st.error(temp_status)
    else:
        if not uploaded_file:
            st.info("Пожалуйста, загрузите файл с историческими данными.")


def load_data(uploaded_file):
    try:
        data = pd.read_csv(uploaded_file, parse_dates=["timestamp"])
        st.success("Данные успешно загружены!")
        st.write("Превью данных:", data.head())
        return data
    except Exception as e:
        st.error(f"Ошибка при загрузке файла: {e}")
        return None


def plot_temperature_series_with_anomalies(city_data, moving_avg, anomaly_points):
    fig, ax = plt.subplots()
    ax.plot(
        city_data.index, city_data["temperature"], label="Температура", color="blue"
    )
    ax.plot(city_data.index, moving_avg, label="Скользящее среднее", color="orange")
    if not anomaly_points.empty:
        ax.scatter(
            anomaly_points["timestamp"],
            anomaly_points["temperature"],
            color="red",
            label="Аномалии",
            zorder=5,
        )
    ax.legend()
    ax.set_xlabel("Дата")
    ax.set_ylabel("Температура (°C)")
    ax.set_title("Температура с аномалиями")
    st.pyplot(fig)


def plot_seasonal_profile(season_profile):
    fig, ax = plt.subplots()
    ax.errorbar(
        season_profile["season"],
        season_profile["average"],
        yerr=2 * season_profile["std"],
        fmt="-o",
        capsize=5,
        label="Средняя температура",
    )
    ax.set_xlabel("Сезон")
    ax.set_ylabel("Температура (°C)")
    ax.set_title("Средняя температура и стандартное отклонение по сезонам")
    ax.legend()
    st.pyplot(fig)


if __name__ == "__main__":
    asyncio.run(process_main_page())
