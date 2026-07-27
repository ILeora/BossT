import discord
from discord.ext import tasks
from datetime import datetime, timedelta, timezone
import json
import os

# === НАСТРОЙКИ ===
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))

# Временная зона МСК (UTC+3)
MOSCOW_TZ = timezone(timedelta(hours=3))

class BossTimerBot(discord.Client):
    async def on_ready(self):
        print(f'Бот {self.user} успешно запущен!')
        self.update_channel_name.start()

    @tasks.loop(minutes=5)
    async def update_channel_name(self):
        channel = self.get_channel(CHANNEL_ID)
        if not channel:
            print("Канал не найден. Проверьте ID канала в Secrets.")
            return

        # Загружаем расписание из файла при каждом запуске,
        # чтобы изменения на GitHub сразу применялись
        try:
            with open('schedule.json', 'r', encoding='utf-8') as f:
                schedule = json.load(f)
        except Exception as e:
            print(f"Ошибка чтения файла расписания: {e}")
            return

        now = datetime.now(MOSCOW_TZ)
        current_day = str(now.weekday())
        current_time = f"{now.hour:02d}:{now.minute:02d}"

        next_boss_time = None
        next_boss_name = None

        # 1. Ищем босса на сегодня, который будет позже текущего времени
        if current_day in schedule:
            day_schedule = schedule[current_day]
            # Сортируем ключи времени (например, "00:30", "14:00"...)
            for b_time in sorted(day_schedule.keys()):
                if b_time > current_time:
                    next_boss_time = b_time
                    next_boss_name = day_schedule[b_time]
                    break

        # 2. Если на сегодня боссов больше нет, ищем первого босса на завтра
        if not next_boss_time:
            next_day = str((int(current_day) + 1) % 7)
            if next_day in schedule and schedule[next_day]:
                first_time = min(schedule[next_day].keys())
                next_boss_time = first_time
                next_boss_name = schedule[next_day][first_time]

        new_name = f"🔒 {next_boss_time} | {next_boss_name}"

        # Обновляем имя, только если оно изменилось (защита от лимитов Discord API)
        if channel.name != new_name:
            await channel.edit(name=new_name)
            print(f"Имя канала успешно изменено на: {new_name}")

intents = discord.Intents.default()
client = BossTimerBot(intents=intents)
client.run(TOKEN)
