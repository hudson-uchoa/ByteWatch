import discord
from discord.ext import commands, tasks
from discord import app_commands
import datetime
import sqlite3
import time
import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# ---------------------------------------------------------
# LOGGING CONFIGURATION (Errors saved to bytewatch.log)
# ---------------------------------------------------------
file_handler = logging.FileHandler(filename='bytewatch.log', encoding='utf-8', mode='a')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger = logging.getLogger('discord')
logger.setLevel(logging.ERROR)
logger.addHandler(file_handler)

# ---------------------------------------------------------
# DATABASE CONFIGURATION (SQLite)
# ---------------------------------------------------------
db_connection = sqlite3.connect('bytewatch.db')
db_cursor = db_connection.cursor()

db_cursor.execute('''
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    status TEXT,
    language TEXT,
    start_time REAL,
    accumulated REAL,
    ai_used TEXT,
    ai_time TEXT
)
''')
db_connection.commit()

# ---------------------------------------------------------
# MAIN BOT CLASS
# ---------------------------------------------------------
class DevBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        self.check_timeouts.start()
        self.weekly_summary.start()
        self.tree.on_error = self.on_app_command_error

    # Global error handling
    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        logger.error(f"Erro no comando /{interaction.command.name} por {interaction.user.name}: {error}")
        error_msg = "❌ Ops! Ocorreu um erro interno. As informações foram gravadas no log."
        if not interaction.response.is_done():
            await interaction.response.send_message(error_msg, ephemeral=True)
        else:
            await interaction.followup.send(error_msg, ephemeral=True)

    # TASK 1: Automatically close sessions paused for more than 2 hours (runs every 5 mins)
    @tasks.loop(minutes=5)
    async def check_timeouts(self):
        current_time = time.time()
        timeout_limit = 2 * 3600  # 2 hours in seconds
        
        db_cursor.execute("SELECT id, start_time FROM sessions WHERE status = 'pausado'")
        for row in db_cursor.fetchall():
            session_id, start_time = row
            if (current_time - start_time) >= timeout_limit:
                db_cursor.execute("UPDATE sessions SET status = 'finalizado', ai_used = 'Não', ai_time = '0' WHERE id = ?", (session_id,))
        db_connection.commit()

    # TASK 2: Automatic Weekly Report (Sunday at 14:00)
    @tasks.loop(minutes=1)
    async def weekly_summary(self):
        current_datetime = datetime.datetime.now()
        if current_datetime.weekday() == 6 and current_datetime.hour == 14 and current_datetime.minute == 0:
            channel_id = os.getenv('DISCORD_CHANNEL_ID')
            if not channel_id:
                return
            
            target_channel = self.get_channel(int(channel_id))
            if not target_channel:
                return

            start_of_week = (current_datetime - datetime.timedelta(days=current_datetime.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
            
            db_cursor.execute("""
                SELECT user_id, SUM(accumulated), GROUP_CONCAT(DISTINCT language), GROUP_CONCAT(DISTINCT ai_used)
                FROM sessions 
                WHERE status = 'finalizado' AND start_time >= ? 
                GROUP BY user_id
            """, (start_of_week.timestamp(),))
            
            query_results = db_cursor.fetchall()
            if not query_results:
                await target_channel.send("📊 **Resumo Semanal:** Nenhuma sessão registrada nesta semana!")
                return
            
            summary_embed = discord.Embed(title="📊 Resumo Semanal de Estudos", color=discord.Color.purple(), timestamp=current_datetime)
            for row in query_results:
                user_id, total_seconds, used_languages, used_ais = row
                minutes, seconds = divmod(int(round(self.total_duration_seconds)), 60)
                hours, minutes = divmod(minutes, 60)
                
                member = self.get_user(int(user_id))
                member_name = member.name if member else f"Dev {user_id}"
                
                clean_ais = [ai for ai in (used_ais.split(',') if used_ais else []) if ai != 'Não']
                formatted_ais = ", ".join(set(clean_ais)) if clean_ais else "Nenhuma"
                formatted_languages = ", ".join(set(used_languages.split(','))) if used_languages else "N/A"
                
                summary_embed.add_field(
                    name=f"👤 {member_name}",
                    value=f"⏱️ **Tempo Total:** {hours}h {minutes}m {seconds}s\n💻 **Linguagens:** {formatted_languages}\n🤖 **IAs Usadas:** {formatted_ais}",
                    inline=False
                )
            await target_channel.send(content="🚀 **Relatório Semanal Liberado!**", embed=summary_embed)

bot_instance = DevBot()

# ---------------------------------------------------------
# MODALS AND VIEWS FOR /START (LANGUAGE SELECTION)
# ---------------------------------------------------------
class CustomLanguageModal(discord.ui.Modal, title='Qual linguagem?'):
    language_input = discord.ui.TextInput(label='Nome da linguagem', style=discord.TextStyle.short, placeholder="Ex: Ruby, Go, Java...")

    async def on_submit(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        current_time = time.time()
        db_cursor.execute("INSERT INTO sessions (user_id, status, language, start_time, accumulated) VALUES (?, ?, ?, ?, ?)",
                       (user_id, 'ativo', self.language_input.value, current_time, 0.0))
        db_connection.commit()
        await interaction.response.edit_message(content=f"⏱️ Cronômetro iniciado para **{self.language_input.value}**! Bom código!", view=None)

class LanguageSelectionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def initialize_session(self, interaction: discord.Interaction, selected_language: str):
        user_id = str(interaction.user.id)
        current_time = time.time()
        db_cursor.execute("INSERT INTO sessions (user_id, status, language, start_time, accumulated) VALUES (?, ?, ?, ?, ?)",
                       (user_id, 'ativo', selected_language, current_time, 0.0))
        db_connection.commit()
        await interaction.response.edit_message(content=f"⏱️ Cronômetro iniciado para **{selected_language}**! Bom código!", view=None)

    @discord.ui.button(label="PHP", emoji="🐘", style=discord.ButtonStyle.secondary, row=0)
    async def button_php(self, interaction: discord.Interaction, button: discord.ui.Button): 
        await self.initialize_session(interaction, "PHP")

    @discord.ui.button(label="C#", emoji="💻", style=discord.ButtonStyle.secondary, row=0)
    async def button_csharp(self, interaction: discord.Interaction, button: discord.ui.Button): 
        await self.initialize_session(interaction, "C#")

    @discord.ui.button(label="Python", emoji="🐍", style=discord.ButtonStyle.secondary, row=0)
    async def button_python(self, interaction: discord.Interaction, button: discord.ui.Button): 
        await self.initialize_session(interaction, "Python")

    @discord.ui.button(label="JavaScript", emoji="🟨", style=discord.ButtonStyle.secondary, row=0)
    async def button_javascript(self, interaction: discord.Interaction, button: discord.ui.Button): 
        await self.initialize_session(interaction, "JavaScript")

    @discord.ui.button(label="TypeScript", emoji="🟦", style=discord.ButtonStyle.secondary, row=0)
    async def button_typescript(self, interaction: discord.Interaction, button: discord.ui.Button): 
        await self.initialize_session(interaction, "TypeScript")

    @discord.ui.button(label="Outra...", emoji="⌨️", style=discord.ButtonStyle.primary, row=1)
    async def button_custom(self, interaction: discord.Interaction, button: discord.ui.Button): 
        await interaction.response.send_modal(CustomLanguageModal())

# ---------------------------------------------------------
# MODALS AND VIEWS FOR /STOP (AI SELECTION)
# ---------------------------------------------------------
class AITimeModal(discord.ui.Modal):
    ai_duration_input = discord.ui.TextInput(label='Tempo na IA? (em min)', required=True, placeholder="Ex: 15")

    def __init__(self, session_id: int, total_duration_seconds: float, session_language: str, ai_identifier: str):
        super().__init__(title=f'Uso do {ai_identifier}')
        self.session_id = session_id
        self.total_duration_seconds = total_duration_seconds
        self.session_language = session_language
        self.ai_identifier = ai_identifier

    async def on_submit(self, interaction: discord.Interaction):
        db_cursor.execute("UPDATE sessions SET status = 'finalizado', accumulated = ?, ai_used = ?, ai_time = ? WHERE id = ?", 
                       (self.total_duration_seconds, self.ai_identifier, self.ai_duration_input.value, self.session_id))
        db_connection.commit()
        
        minutes, seconds = divmod(int(self.total_duration_seconds), 60)
        hours, minutes = divmod(minutes, 60)
        
        result_embed = discord.Embed(title="✅ Sessão Finalizada", color=discord.Color.green())
        result_embed.add_field(name="Linguagem", value=self.session_language, inline=True)
        result_embed.add_field(name="Tempo Total", value=f"{hours}h {minutes}m {seconds}s", inline=True)
        result_embed.add_field(name="IA Utilizada", value=f"{self.ai_identifier} ({self.ai_duration_input.value} min)", inline=False)
        
        await interaction.response.edit_message(content=None, embed=result_embed, view=None)

class CustomAIModal(discord.ui.Modal, title='Qual IA você usou?'):
    custom_ai_input = discord.ui.TextInput(label='Nome da IA', required=True, placeholder="Ex: Tabnine, Llama...")
    ai_duration_input = discord.ui.TextInput(label='Tempo na IA? (em min)', required=True, placeholder="Ex: 15")

    def __init__(self, session_id: int, total_duration_seconds: float, session_language: str):
        super().__init__()
        self.session_id = session_id
        self.total_duration_seconds = total_duration_seconds
        self.session_language = session_language

    async def on_submit(self, interaction: discord.Interaction):
        db_cursor.execute("UPDATE sessions SET status = 'finalizado', accumulated = ?, ai_used = ?, ai_time = ? WHERE id = ?", 
                       (self.total_duration_seconds, self.custom_ai_input.value, self.ai_duration_input.value, self.session_id))
        db_connection.commit()
        
        minutes, seconds = divmod(int(self.total_duration_seconds), 60)
        hours, minutes = divmod(minutes, 60)
        
        result_embed = discord.Embed(title="✅ Sessão Finalizada", color=discord.Color.green())
        result_embed.add_field(name="Linguagem", value=self.session_language, inline=True)
        result_embed.add_field(name="Tempo Total", value=f"{hours}h {minutes}m {seconds}s", inline=True)
        result_embed.add_field(name="IA Utilizada", value=f"{self.custom_ai_input.value} ({self.ai_duration_input.value} min)", inline=False)
        
        await interaction.response.edit_message(content=None, embed=result_embed, view=None)

class StopSessionView(discord.ui.View):
    def __init__(self, session_id: int, total_duration_seconds: float, session_language: str):
        super().__init__(timeout=None)
        self.session_id = session_id
        self.total_duration_seconds = total_duration_seconds
        self.session_language = session_language

    async def finalize_session_with_ai(self, interaction: discord.Interaction, selected_ai: str):
        await interaction.response.send_modal(AITimeModal(self.session_id, self.total_duration_seconds, self.session_language, selected_ai))

    @discord.ui.button(label="ChatGPT", emoji="🤖", style=discord.ButtonStyle.secondary, row=0)
    async def button_chatgpt(self, interaction: discord.Interaction, button: discord.ui.Button): 
        await self.finalize_session_with_ai(interaction, "ChatGPT")

    @discord.ui.button(label="Copilot", emoji="✈️", style=discord.ButtonStyle.secondary, row=0)
    async def button_copilot(self, interaction: discord.Interaction, button: discord.ui.Button): 
        await self.finalize_session_with_ai(interaction, "GitHub Copilot")

    @discord.ui.button(label="Gemini", emoji="✨", style=discord.ButtonStyle.secondary, row=0)
    async def button_gemini(self, interaction: discord.Interaction, button: discord.ui.Button): 
        await self.finalize_session_with_ai(interaction, "Gemini")

    @discord.ui.button(label="Claude", emoji="🧠", style=discord.ButtonStyle.secondary, row=0)
    async def button_claude(self, interaction: discord.Interaction, button: discord.ui.Button): 
        await self.finalize_session_with_ai(interaction, "Claude")

    @discord.ui.button(label="Cursor", emoji="🖱️", style=discord.ButtonStyle.secondary, row=0)
    async def button_cursor(self, interaction: discord.Interaction, button: discord.ui.Button): 
        await self.finalize_session_with_ai(interaction, "Cursor")

    @discord.ui.button(label="Outra IA...", emoji="⌨️", style=discord.ButtonStyle.primary, row=1)
    async def button_custom_ai(self, interaction: discord.Interaction, button: discord.ui.Button): 
        await interaction.response.send_modal(CustomAIModal(self.session_id, self.total_duration_seconds, self.session_language))

    @discord.ui.button(label="Não usei IA", emoji="🚫", style=discord.ButtonStyle.danger, row=1)
    async def button_no_ai(self, interaction: discord.Interaction, button: discord.ui.Button):
        db_cursor.execute("UPDATE sessions SET status = 'finalizado', accumulated = ?, ai_used = 'Não', ai_time = '0' WHERE id = ?", 
                       (self.total_duration_seconds, self.session_id))
        db_connection.commit()

        minutes, seconds = divmod(int(self.total_duration_seconds), 60)
        hours, minutes = divmod(minutes, 60)
        
        result_embed = discord.Embed(title="✅ Sessão Finalizada", color=discord.Color.green())
        result_embed.add_field(name="Linguagem", value=self.session_language, inline=True)
        result_embed.add_field(name="Tempo Total", value=f"{hours}h {minutes}m {seconds}s", inline=True)
        result_embed.add_field(name="IA Utilizada", value="Nenhuma 🚫", inline=False)
        
        await interaction.response.edit_message(content=None, embed=result_embed, view=None)

# ---------------------------------------------------------
# SLASH COMMANDS (/)
# ---------------------------------------------------------
@bot_instance.tree.command(name="start", description="Começa a contar o tempo da sessão.")
async def command_start(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    db_cursor.execute("SELECT id FROM sessions WHERE user_id = ? AND status != 'finalizado'", (user_id,))
    if db_cursor.fetchone():
        await interaction.response.send_message("⚠️ Você já tem uma sessão em andamento! Use /stop ou /pause.", ephemeral=True)
        return
    await interaction.response.send_message("⏱️ Qual linguagem você vai estudar agora?", view=LanguageSelectionView(), ephemeral=False)

@bot_instance.tree.command(name="pause", description="Pausa o contador (por no máximo 2 horas).")
async def command_pause(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    db_cursor.execute("SELECT id, start_time, accumulated FROM sessions WHERE user_id = ? AND status = 'ativo'", (user_id,))
    active_session = db_cursor.fetchone()
    if not active_session:
        await interaction.response.send_message("❌ Nenhuma sessão ativa para pausar.", ephemeral=True)
        return
        
    session_id, start_time, accumulated_time = active_session
    elapsed_time = time.time() - start_time
    updated_accumulated_time = accumulated_time + elapsed_time
    
    db_cursor.execute("UPDATE sessions SET status = 'pausado', accumulated = ?, start_time = ? WHERE id = ?", (updated_accumulated_time, time.time(), session_id))
    db_connection.commit()
    await interaction.response.send_message("⏸️ Tempo pausado. Lembre-se: em 2 horas a sessão será encerrada automaticamente!", ephemeral=False)

@bot_instance.tree.command(name="resume", description="Resume o contador parado.")
async def command_resume(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    db_cursor.execute("SELECT id, language FROM sessions WHERE user_id = ? AND status = 'pausado'", (user_id,))
    paused_session = db_cursor.fetchone()
    if not paused_session:
        await interaction.response.send_message("❌ Você não tem nenhuma sessão pausada.", ephemeral=True)
        return
        
    session_id, session_language = paused_session
    db_cursor.execute("UPDATE sessions SET status = 'ativo', start_time = ? WHERE id = ?", (time.time(), session_id))
    db_connection.commit()
    await interaction.response.send_message(f"▶️ Sessão de **{session_language}** retomada!", ephemeral=False)

@bot_instance.tree.command(name="stop", description="Finaliza a sessão atual.")
async def command_stop(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    db_cursor.execute("SELECT id, status, start_time, accumulated, language FROM sessions WHERE user_id = ? AND status != 'finalizado'", (user_id,))
    ongoing_session = db_cursor.fetchone()
    if not ongoing_session:
        await interaction.response.send_message("❌ Você não tem nenhuma sessão em andamento.", ephemeral=True)
        return
        
    session_id, session_status, start_time, accumulated_time, session_language = ongoing_session
    total_duration = accumulated_time
    if session_status == 'ativo':
        total_duration += (time.time() - start_time)
        
    await interaction.response.send_message("🛑 Sessão pausada para finalização.\n\n**Qual IA você usou para te ajudar hoje?**", view=StopSessionView(session_id, total_duration, session_language), ephemeral=False)

@bot_instance.tree.command(name="ranking", description="Mostra o total de horas registradas na semana.")
async def command_ranking(interaction: discord.Interaction):
    current_date = datetime.datetime.now()
    start_of_week = (current_date - datetime.timedelta(days=current_date.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    
    db_cursor.execute("SELECT user_id, SUM(accumulated) as total FROM sessions WHERE status = 'finalizado' AND start_time >= ? GROUP BY user_id ORDER BY total DESC", (start_of_week.timestamp(),))
    ranking_results = db_cursor.fetchall()

    if not ranking_results:
        await interaction.response.send_message("📊 Ainda não há horas registradas nesta semana. Bora codar!", ephemeral=False)
        return

    ranking_embed = discord.Embed(title="🏆 Ranking da Semana", description="Total de horas estudadas desde segunda-feira:", color=discord.Color.gold())
    
    top1_id = ranking_results[0][0]
    top1_user = bot_instance.get_user(int(top1_id))
    if not top1_user:
        try:
            top1_user = await bot_instance.fetch_user(int(top1_id))
        except:
            pass
            
    if top1_user and top1_user.display_avatar:
        ranking_embed.set_thumbnail(url=top1_user.display_avatar.url)

    posicao = 1
    medalhas = ["🥇", "🥈", "🥉"]

    for row in ranking_results:
        user_id, total_seconds = row
        minutes, seconds = divmod(int(round(total_seconds or 0)), 60)
        hours, minutes = divmod(minutes, 60)
        
        medalha = medalhas[posicao - 1] if posicao <= 3 else "🏅"
        
        ranking_embed.add_field(
            name=f"{medalha} {posicao}º Lugar", 
            value=f"**Dev:** <@{user_id}>\n**Tempo:** {hours}h {minutes}m {seconds}s", 
            inline=False
        )
        posicao += 1

    await interaction.response.send_message(embed=ranking_embed)

# ---------------------------------------------------------
# INITIALIZATION
# ---------------------------------------------------------
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
bot_instance.run(DISCORD_TOKEN)