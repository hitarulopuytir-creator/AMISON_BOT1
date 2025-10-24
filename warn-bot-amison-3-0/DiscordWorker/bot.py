import discord
from discord.ext import commands
from discord.ui import View, Button
import json
import os
import re
from datetime import datetime

# 🔹 1. Flask-сервер для UptimeRobot
from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def run_web():
    try:
        app.run(host="0.0.0.0", port=5000, use_reloader=False)
    except OSError as e:
        print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Flask сервер не смог запуститься: {e}')

threading.Thread(target=run_web, daemon=True).start()


# 🔹 2. Настройки Discord
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

WARNS_FILE = 'warns.json'
TICKETS_FILE = 'whitelist_tickets.json'

# Константы ID ролей
ADMIN_ROLE_ID = 1193894492663713792
MOD_ROLE_ID = 1037412954481639476
OWNER_ROLE_ID = 1037411767611052182
PERMA_BAN_ROLE_ID = 1424009252137205864
LOG_CHANNEL_ID = 1431367741553639498


# 🔹 3. Работа с JSON-файлом варнов
def load_warns():
    if os.path.exists(WARNS_FILE):
        with open(WARNS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_warns(warns):
    with open(WARNS_FILE, 'w') as f:
        json.dump(warns, f, indent=4)

warns_data = load_warns()


# 🔹 4. Работа с заявками в белый список
def load_tickets():
    """Загрузка данных заявок"""
    try:
        if os.path.exists(TICKETS_FILE):
            with open(TICKETS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"last_ticket_number": 0, "tickets": {}}
    except Exception as e:
        print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] ОШИБКА при загрузке заявок: {e}')
        return {"last_ticket_number": 0, "tickets": {}}

def save_tickets(data):
    """Сохранение данных заявок"""
    try:
        with open(TICKETS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Заявки успешно сохранены')
    except Exception as e:
        print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] ОШИБКА при сохранении заявок: {e}')

def get_next_ticket_number(guild_id):
    """Получение следующего номера заявки"""
    try:
        data = load_tickets()
        data['last_ticket_number'] += 1
        save_tickets(data)
        print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Выдан номер заявки: {data["last_ticket_number"]}')
        return data['last_ticket_number']
    except Exception as e:
        print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] ОШИБКА при получении номера заявки: {e}')
        return 1

def create_ticket(guild_id, user_id, channel_id, nickname):
    """Создание новой заявки"""
    try:
        data = load_tickets()
        ticket_number = data['last_ticket_number']
        
        ticket_key = f"{guild_id}_{user_id}_{ticket_number}"
        data['tickets'][ticket_key] = {
            'ticket_number': ticket_number,
            'guild_id': str(guild_id),
            'user_id': str(user_id),
            'channel_id': str(channel_id),
            'nickname': nickname,
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        save_tickets(data)
        print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Создана заявка #{ticket_number} для пользователя {user_id}')
        return ticket_number
    except Exception as e:
        print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] ОШИБКА при создании заявки: {e}')
        return None

def get_user_tickets(guild_id, user_id):
    """Получение истории заявок пользователя"""
    try:
        data = load_tickets()
        user_tickets = []
        
        for ticket_key, ticket_data in data['tickets'].items():
            if ticket_data['guild_id'] == str(guild_id) and ticket_data['user_id'] == str(user_id):
                user_tickets.append(ticket_data)
        
        user_tickets.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Найдено {len(user_tickets)} заявок для пользователя {user_id}')
        return user_tickets
    except Exception as e:
        print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] ОШИБКА при получении истории заявок: {e}')
        return []

def update_ticket_status(guild_id, user_id, ticket_number, status):
    """Обновление статуса заявки"""
    try:
        data = load_tickets()
        ticket_key = f"{guild_id}_{user_id}_{ticket_number}"
        
        if ticket_key in data['tickets']:
            data['tickets'][ticket_key]['status'] = status
            data['tickets'][ticket_key]['updated_at'] = datetime.now().isoformat()
            save_tickets(data)
            print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Статус заявки #{ticket_number} обновлен на: {status}')
            return True
        else:
            print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] ОШИБКА: заявка #{ticket_number} не найдена')
            return False
    except Exception as e:
        print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] ОШИБКА при обновлении статуса заявки: {e}')
        return False


# 🔹 5. Функция отправки уведомлений
async def send_notification(bot, guild_id, ticket_number, decision, username):
    """Отправка уведомления о решении по заявке"""
    try:
        guild = bot.get_guild(int(guild_id))
        if not guild:
            print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] ОШИБКА: сервер {guild_id} не найден')
            return
        
        log_channel = guild.get_channel(LOG_CHANNEL_ID)
        if not log_channel:
            print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] ОШИБКА: канал логов не найден')
            return
        
        decision_text = "Принято" if decision == "approved" else "Отказано"
        color = discord.Color.green() if decision == "approved" else discord.Color.red()
        
        embed = discord.Embed(
            title=f"📋 Заявка #{ticket_number}",
            description=f"**Статус:** {decision_text}\n**Пользователь:** {username}",
            color=color,
            timestamp=datetime.now()
        )
        
        await log_channel.send(embed=embed)
        print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Уведомление отправлено: Заявка #{ticket_number} — {decision_text} — {username}')
    except Exception as e:
        print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] ОШИБКА при отправке уведомления: {e}')


# 🔹 6. Discord Views для управления заявками

class WhitelistDecisionView(View):
    """Первая группа кнопок: принятие/отказ"""
    
    def __init__(self, ticket_number, guild_id, user_id, username):
        super().__init__(timeout=None)
        self.ticket_number = ticket_number
        self.guild_id = guild_id
        self.user_id = user_id
        self.username = username
        
        approve_button = Button(
            label="Добавлен в белый список",
            style=discord.ButtonStyle.success,
            custom_id=f"whitelist_approve_{ticket_number}"
        )
        approve_button.callback = self.approve_callback
        
        deny_button = Button(
            label="Отказ в белом списке",
            style=discord.ButtonStyle.danger,
            custom_id=f"whitelist_deny_{ticket_number}"
        )
        deny_button.callback = self.deny_callback
        
        self.add_item(approve_button)
        self.add_item(deny_button)
    
    async def approve_callback(self, interaction: discord.Interaction):
        """Обработка одобрения заявки"""
        try:
            if not await self.check_permissions(interaction):
                return
            
            update_ticket_status(self.guild_id, self.user_id, self.ticket_number, 'approved')
            await send_notification(bot, self.guild_id, self.ticket_number, 'approved', self.username)
            
            await interaction.response.edit_message(
                content=f"✅ Заявка #{self.ticket_number} одобрена администратором {interaction.user.mention}",
                view=WhitelistCloseView(self.ticket_number, self.guild_id, self.user_id)
            )
            
            print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Заявка #{self.ticket_number} одобрена пользователем {interaction.user.name}')
        except Exception as e:
            print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] ОШИБКА при одобрении заявки: {e}')
            await interaction.response.send_message(f'❌ Ошибка при обработке заявки: {str(e)}', ephemeral=True)
    
    async def deny_callback(self, interaction: discord.Interaction):
        """Обработка отказа в заявке"""
        try:
            if not await self.check_permissions(interaction):
                return
            
            update_ticket_status(self.guild_id, self.user_id, self.ticket_number, 'denied')
            await send_notification(bot, self.guild_id, self.ticket_number, 'denied', self.username)
            
            await interaction.response.edit_message(
                content=f"❌ Заявка #{self.ticket_number} отклонена администратором {interaction.user.mention}",
                view=WhitelistCloseView(self.ticket_number, self.guild_id, self.user_id)
            )
            
            print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Заявка #{self.ticket_number} отклонена пользователем {interaction.user.name}')
        except Exception as e:
            print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] ОШИБКА при отклонении заявки: {e}')
            await interaction.response.send_message(f'❌ Ошибка при обработке заявки: {str(e)}', ephemeral=True)
    
    async def check_permissions(self, interaction: discord.Interaction):
        """Проверка прав доступа (админ или модератор)"""
        member = interaction.user
        has_permission = any(role.id in [ADMIN_ROLE_ID, MOD_ROLE_ID] for role in member.roles)
        
        if not has_permission:
            await interaction.response.send_message('❌ У вас нет прав для выполнения этого действия!', ephemeral=True)
            print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Отказ в доступе для {member.name} (нет прав админа/модератора)')
        
        return has_permission


class WhitelistCloseView(View):
    """Вторая группа кнопок: закрытие тикета"""
    
    def __init__(self, ticket_number, guild_id, user_id):
        super().__init__(timeout=None)
        self.ticket_number = ticket_number
        self.guild_id = guild_id
        self.user_id = user_id
        
        close_button = Button(
            label="Закрыть тикет",
            style=discord.ButtonStyle.danger,
            custom_id=f"whitelist_close_{ticket_number}"
        )
        close_button.callback = self.close_callback
        
        self.add_item(close_button)
    
    async def close_callback(self, interaction: discord.Interaction):
        """Обработка закрытия тикета"""
        try:
            if not await self.check_permissions(interaction):
                return
            
            channel = interaction.channel
            
            overwrites = channel.overwrites
            for target, overwrite in overwrites.items():
                if target != interaction.guild.me and target.id != OWNER_ROLE_ID:
                    overwrite.send_messages = False
                    await channel.set_permissions(target, overwrite=overwrite)
            
            update_ticket_status(self.guild_id, self.user_id, self.ticket_number, 'closed')
            
            await interaction.response.edit_message(
                content=f"🔒 Тикет #{self.ticket_number} закрыт администратором {interaction.user.mention}",
                view=WhitelistManageView(self.ticket_number, self.guild_id, self.user_id, channel.id)
            )
            
            print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Тикет #{self.ticket_number} закрыт пользователем {interaction.user.name}')
        except Exception as e:
            print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] ОШИБКА при закрытии тикета: {e}')
            await interaction.response.send_message(f'❌ Ошибка при закрытии тикета: {str(e)}', ephemeral=True)
    
    async def check_permissions(self, interaction: discord.Interaction):
        """Проверка прав доступа (только владелец)"""
        member = interaction.user
        has_permission = any(role.id == OWNER_ROLE_ID for role in member.roles)
        
        if not has_permission:
            await interaction.response.send_message('❌ У вас нет прав для выполнения этого действия!', ephemeral=True)
            print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Отказ в доступе для {member.name} (нет прав владельца)')
        
        return has_permission


class WhitelistManageView(View):
    """Третья группа кнопок: удаление/открытие тикета"""
    
    def __init__(self, ticket_number, guild_id, user_id, channel_id):
        super().__init__(timeout=None)
        self.ticket_number = ticket_number
        self.guild_id = guild_id
        self.user_id = user_id
        self.channel_id = channel_id
        
        delete_button = Button(
            label="Удалить тикет",
            style=discord.ButtonStyle.danger,
            custom_id=f"whitelist_delete_{ticket_number}"
        )
        delete_button.callback = self.delete_callback
        
        reopen_button = Button(
            label="Открыть тикет",
            style=discord.ButtonStyle.success,
            custom_id=f"whitelist_reopen_{ticket_number}"
        )
        reopen_button.callback = self.reopen_callback
        
        self.add_item(delete_button)
        self.add_item(reopen_button)
    
    async def delete_callback(self, interaction: discord.Interaction):
        """Обработка удаления тикета"""
        try:
            if not await self.check_permissions(interaction):
                return
            
            channel = interaction.channel
            
            update_ticket_status(self.guild_id, self.user_id, self.ticket_number, 'deleted')
            
            await interaction.response.send_message(
                f"🗑️ Тикет #{self.ticket_number} будет удален через 5 секунд...",
                ephemeral=False
            )
            
            print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Тикет #{self.ticket_number} удален пользователем {interaction.user.name}')
            
            import asyncio
            await asyncio.sleep(5)
            await channel.delete()
            
        except Exception as e:
            print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] ОШИБКА при удалении тикета: {e}')
            if not interaction.response.is_done():
                await interaction.response.send_message(f'❌ Ошибка при удалении тикета: {str(e)}', ephemeral=True)
    
    async def reopen_callback(self, interaction: discord.Interaction):
        """Обработка открытия тикета"""
        try:
            if not await self.check_permissions(interaction):
                return
            
            channel = interaction.channel
            guild = interaction.guild
            
            admin_role = guild.get_role(ADMIN_ROLE_ID)
            mod_role = guild.get_role(MOD_ROLE_ID)
            member = guild.get_member(int(self.user_id))
            
            if admin_role:
                await channel.set_permissions(admin_role, send_messages=True, read_messages=True)
            if mod_role:
                await channel.set_permissions(mod_role, send_messages=True, read_messages=True)
            if member:
                await channel.set_permissions(member, send_messages=True, read_messages=True)
            
            update_ticket_status(self.guild_id, self.user_id, self.ticket_number, 'reopened')
            
            await interaction.response.edit_message(
                content=f"🔓 Тикет #{self.ticket_number} открыт администратором {interaction.user.mention}",
                view=WhitelistCloseView(self.ticket_number, self.guild_id, self.user_id)
            )
            
            print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Тикет #{self.ticket_number} открыт пользователем {interaction.user.name}')
        except Exception as e:
            print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] ОШИБКА при открытии тикета: {e}')
            await interaction.response.send_message(f'❌ Ошибка при открытии тикета: {str(e)}', ephemeral=True)
    
    async def check_permissions(self, interaction: discord.Interaction):
        """Проверка прав доступа (только владелец)"""
        member = interaction.user
        has_permission = any(role.id == OWNER_ROLE_ID for role in member.roles)
        
        if not has_permission:
            await interaction.response.send_message('❌ У вас нет прав для выполнения этого действия!', ephemeral=True)
            print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Отказ в доступе для {member.name} (нет прав владельца)')
        
        return has_permission


# 🔹 7. События Discord
@bot.event
async def on_ready():
    print(f'Бот {bot.user} успешно запущен!')
    print(f'ID: {bot.user.id}')
    print('------')
    
    print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Регистрация persistent views...')
    
    data = load_tickets()
    for ticket_key, ticket_data in data['tickets'].items():
        ticket_number = ticket_data['ticket_number']
        guild_id = ticket_data['guild_id']
        user_id = ticket_data['user_id']
        username = ticket_data.get('nickname', 'Unknown')
        status = ticket_data.get('status', 'pending')
        channel_id = ticket_data.get('channel_id')
        
        if status == 'pending':
            bot.add_view(WhitelistDecisionView(ticket_number, guild_id, user_id, username))
        elif status in ['approved', 'denied', 'reopened']:
            bot.add_view(WhitelistCloseView(ticket_number, guild_id, user_id))
        elif status == 'closed':
            bot.add_view(WhitelistManageView(ticket_number, guild_id, user_id, channel_id))
    
    print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Persistent views зарегистрированы')


@bot.event
async def on_message(message):
    if message.author.bot and message.embeds:
        for embed in message.embeds:
            if embed.author and '[WARN]' in str(embed.author.name):
                try:
                    user_id = None
                    for field in embed.fields:
                        if field.name == 'User':
                            user_mention = field.value
                            match = re.search(r'<@(\d+)>', user_mention)
                            if match:
                                user_id = match.group(1)
                                break

                    if not user_id:
                        print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] ОШИБКА: ID пользователя не найден в embed')
                        continue

                    guild_id = str(message.guild.id)

                    if guild_id not in warns_data:
                        warns_data[guild_id] = {}

                    if user_id not in warns_data[guild_id]:
                        warns_data[guild_id][user_id] = 0

                    warns_data[guild_id][user_id] += 1
                    save_warns(warns_data)

                    warn_count = warns_data[guild_id][user_id]

                    member = message.guild.get_member(int(user_id))
                    if member:
                        print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Варн выдан: {member.name} ({user_id}) - Всего варнов: {warn_count}')

                        if warn_count == 1:
                            role = discord.utils.get(message.guild.roles, name='Warn1lvl')
                            if role:
                                await member.add_roles(role)
                                print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Роль Warn1lvl выдана: {member.name}')
                            else:
                                print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] ОШИБКА: Роль Warn1lvl не найдена!')

                        elif warn_count == 2:
                            role1 = discord.utils.get(message.guild.roles, name='Warn1lvl')
                            role2 = discord.utils.get(message.guild.roles, name='Warn2lvl')

                            if role1 and role1 in member.roles:
                                await member.remove_roles(role1)
                                print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Роль Warn1lvl снята: {member.name}')

                            if role2:
                                await member.add_roles(role2)
                                print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Роль Warn2lvl выдана: {member.name}')
                            else:
                                print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] ОШИБКА: Роль Warn2lvl не найдена!')

                        elif warn_count > 2:
                            print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] У пользователя {member.name} уже {warn_count} варнов')
                    else:
                        print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] ОШИБКА: Участник с ID {user_id} не найден на сервере')

                except Exception as e:
                    print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] ОШИБКА при обработке варна: {e}')

    await bot.process_commands(message)


# 🔹 8. Команда /nick для заявки в белый список
@bot.command(name='nick')
async def check_nickname(ctx, requested_nick: str):
    """
    Команда для создания заявки на добавление в белый список.
    Создаёт приватный канал для администрации и модерации.
    """
    try:
        guild = ctx.guild
        member = ctx.author
        
        admin_role = guild.get_role(ADMIN_ROLE_ID)
        mod_role = guild.get_role(MOD_ROLE_ID)
        
        if not admin_role or not mod_role:
            await ctx.send('❌ Ошибка: роли администрации или модерации не найдены на сервере!')
            print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] ОШИБКА: роли для команды /nick не найдены')
            return
        
        ticket_number = get_next_ticket_number(str(guild.id))
        
        channel_name = f'заявка-в-белый-список-{ticket_number}'
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            mod_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        category = discord.utils.get(guild.categories, name='Проверки') or None
        channel = await guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            category=category,
            topic=f'Заявка в белый список #{ticket_number} для {member.name}'
        )
        
        create_ticket(str(guild.id), str(member.id), str(channel.id), requested_nick)
        
        account_age = datetime.now(member.created_at.tzinfo) - member.created_at
        account_age_days = account_age.days
        
        perma_ban_role = guild.get_role(PERMA_BAN_ROLE_ID)
        has_perma_ban = perma_ban_role in member.roles if perma_ban_role else False
        
        previous_tickets = get_user_tickets(str(guild.id), str(member.id))
        previous_count = len(previous_tickets) - 1
        
        embed = discord.Embed(
            title='🔍 Заявка в белый список',
            description=f'Участник {member.mention} запросил добавление в белый список: **{requested_nick}**',
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name='🎫 Номер заявки',
            value=f'#{ticket_number}',
            inline=True
        )
        
        embed.add_field(
            name='📜 Предыдущие заявки',
            value=f'{previous_count} заявок' if previous_count > 0 else 'Первая заявка',
            inline=True
        )
        
        embed.add_field(
            name='📅 Дата регистрации аккаунта',
            value=f'{member.created_at.strftime("%d.%m.%Y %H:%M")} UTC\n({account_age_days} дней назад)',
            inline=False
        )
        
        embed.add_field(
            name='📅 Присоединился к серверу',
            value=f'{member.joined_at.strftime("%d.%m.%Y %H:%M")} UTC' if member.joined_at else 'Неизвестно',
            inline=False
        )
        
        embed.add_field(
            name='🚫 Роль "пермач бан на сервере в майнкрафте"',
            value='✅ Есть' if has_perma_ban else '❌ Нет',
            inline=False
        )
        
        warnings = []
        
        if account_age_days < 30:
            warnings.append(f'⚠️ **ВНИМАНИЕ**: Аккаунт создан недавно ({account_age_days} дней)')
        
        if has_perma_ban:
            warnings.append('⚠️ **ВНИМАНИЕ**: У участника есть роль "пермач бан на сервере в майнкрафте"')
        
        if previous_count > 0:
            warnings.append(f'⚠️ **ВНИМАНИЕ**: У участника уже есть {previous_count} предыдущих заявок')
        
        if warnings:
            embed.add_field(
                name='⚠️ Отклонения',
                value='\n'.join(warnings),
                inline=False
            )
            embed.color = discord.Color.orange()
        else:
            embed.add_field(
                name='✅ Статус',
                value='Проверка пройдена, отклонений не обнаружено',
                inline=False
            )
            embed.color = discord.Color.green()
        
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f'ID участника: {member.id}')
        
        view = WhitelistDecisionView(ticket_number, str(guild.id), str(member.id), member.name)
        
        await channel.send(
            f'{admin_role.mention} {mod_role.mention}\n\nНовая заявка в белый список!',
            embed=embed,
            view=view
        )
        
        await ctx.send(f'✅ Создана заявка #{ticket_number}: {channel.mention}')
        
        print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Создана заявка #{ticket_number} для {member.name} (ник: {requested_nick})')
        
    except Exception as e:
        await ctx.send(f'❌ Произошла ошибка при создании заявки: {str(e)}')
        print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] ОШИБКА в команде /nick: {e}')


# 🔹 9. Запуск Discord-бота
TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    print('ОШИБКА: Токен Discord не найден!')
    print('Пожалуйста, добавьте DISCORD_TOKEN в переменные окружения')
else:
    bot.run(TOKEN)
