import discord
from datetime import datetime, timedelta, timezone
import json
import os

# === НАСТРОЙКИ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ===
TOKEN = os.getenv('DISCORD_TOKEN')
BOSS_CHANNEL_ID = os.getenv('DISCORD_CHANNEL_ID')
TIME_CHANNEL_ID = os.getenv('DISCORD_TIME_CHANNEL_ID')

# Временная зона МСК (UTC+3)
MOSCOW_TZ = timezone(timedelta(hours=3))


def get_day_night_status(now_dt):
    """
    Вычисляет фазу дня/ночи и время следующего переключения.
    Полный цикл — 4 часа (240 минут):
      - 200 минут (3ч 20м) — ДЕНЬ
      - 40 минут — НОЧЬ
    Базовая точка отсчета: 03:20 МСК (200 минут от 00:00).
    """
    minutes_since_midnight = now_dt.hour * 60 + now_dt.minute
    base_offset = 200  # 03:20 в минутах от 00:00

    # Внутри 240-минутного цикла
    cycle_minutes = (minutes_since_midnight - base_offset) % 240

    if cycle_minutes < 200:
        # Сейчас ДЕНЬ -> следующий этап НОЧЬ
        is_day = True
        minutes_until_change = 200 - cycle_minutes
    else:
        # Сейчас НОЧЬ -> следующий этап ДЕНЬ
        is_day = False
        minutes_until_change = 240 - cycle_minutes

    # Точный расчет времени следующей смены
    seconds_until_change = minutes_until_change * 60 - now_dt.second
    next_change_dt = now_dt + timedelta(seconds=seconds_until_change)

    time_str = next_change_dt.strftime("%H.%M")

    if is_day:
        return f"🌞| Ночь в {time_str}"
    else:
        return f"🌙| День в {time_str}"


def get_next_boss_status(now_dt):
    """
    Загружает schedule.json и определяет следующего босса.
    """
    try:
        with open('schedule.json', 'r', encoding='utf-8') as f:
            schedule = json.load(f)
    except Exception as e:
        print(f"Ошибка чтения файла schedule.json: {e}")
        return None

    current_day = str(now_dt.weekday())
    current_time = f"{now_dt.hour:02d}:{now_dt.minute:02d}"

    next_boss_time = None
    next_boss_name = None

    # Ищем босса на сегодня
    if current_day in schedule:
        day_schedule = schedule[current_day]
        for b_time in sorted(day_schedule.keys()):
            if b_time > current_time:
                next_boss_time = b_time
                next_boss_name = day_schedule[b_time]
                break

    # Если на сегодня боссов больше нет, ищем на завтра
    if not next_boss_time:
        next_day = str((int(current_day) + 1) % 7)
        if next_day in schedule and schedule[next_day]:
            first_time = min(schedule[next_day].keys())
            next_boss_time = first_time
            next_boss_name = schedule[next_day][first_time]

    if next_boss_time and next_boss_name:
        return f"{next_boss_time} {next_boss_name}".strip()
    
    return None


class CombinedBot(discord.Client):
    async def on_ready(self):
        print(f'Бот {self.user} успешно запущен!')
        now = datetime.now(MOSCOW_TZ)

        # --- 1. ОБНОВЛЕНИЕ КАНАЛА БОССОВ ---
        if BOSS_CHANNEL_ID:
            try:
                boss_channel = await self.fetch_channel(int(BOSS_CHANNEL_ID))
                new_boss_name = get_next_boss_status(now)

                if new_boss_name:
                    if boss_channel.name != new_boss_name:
                        await boss_channel.edit(name=new_boss_name)
                        print(f"[Боссы] Имя канала изменено на: {new_boss_name}")
                    else:
                        print("[Боссы] Имя канала уже актуально.")
            except Exception as e:
                print(f"[Боссы] Ошибка при обновлении канала: {e}")
        else:
            print("[Боссы] DISCORD_CHANNEL_ID не задан в переменных окружения.")

        # --- 2. ОБНОВЛЕНИЕ КАНАЛА ВРЕМЕНИ СУТОК ---
        if TIME_CHANNEL_ID:
            try:
                time_channel = await self.fetch_channel(int(TIME_CHANNEL_ID))
                new_time_name = get_day_night_status(now)

                if time_channel.name != new_time_name:
                    await time_channel.edit(name=new_time_name)
                    print(f"[Время] Имя канала изменено на: {new_time_name}")
                else:
                    print("[Время] Имя канала уже актуально.")
            except Exception as e:
                print(f"[Время] Ошибка при обновлении канала: {e}")
        else:
            print("[Время] DISCORD_TIME_CHANNEL_ID не задан в переменных окружения.")

        print("Завершение работы скрипта...")
        await self.close()


if __name__ == "__main__":
    intents = discord.Intents.default()
    client = CombinedBot(intents=intents)
    client.run(TOKEN)
