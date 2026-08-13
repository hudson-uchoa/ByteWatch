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

# Table for study sessions (supports projects and AI tracking)
db_cursor.execute('''
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    status TEXT,
    language TEXT,
    project_name TEXT,
    start_time REAL,
    accumulated REAL,
    ai_used TEXT,
    ai_time TEXT
)
''')

# Table for user projects and progress tracking
db_cursor.execute('''
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    name TEXT,
    progress INTEGER DEFAULT 0,
    status TEXT DEFAULT 'ativo'
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
                minutes, seconds = divmod(int(round(total_seconds or 0)), 60)
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
# INTERACTIVE VIEWS FOR /START (PROJECT & LANGUAGE SELECTION)
# ---------------------------------------------------------
class CustomLanguageModal(discord.ui.Modal, title='Qual linguagem?'):
    language_input = discord.ui.TextInput(label='Nome da linguagem', style=discord.TextStyle.short, placeholder="Ex: Ruby, Go, Java...")

    def __init__(self, project_name: str):
        super().__init__()
        self.project_name = project_name

    async def on_submit(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        current_time = time.time()
        db_cursor.execute("INSERT INTO sessions (user_id, status, language, project_name, start_time, accumulated, ai_used, ai_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (user_id, 'ativo', self.language_input.value, self.project_name, current_time, 0.0, '', ''))
        db_connection.commit()
        
        msg = (
            f"⏱️ Sessão iniciada no projeto **{self.project_name}** usando **{self.language_input.value}**! Bons estudos!\n"
            f"💡 *Dica: Quer ver quanto tempo já passou sem parar o cronômetro? Use `/status` a qualquer momento!*"
        )
        await interaction.response.edit_message(content=msg, view=None)

class LanguageSelectionView(discord.ui.View):
    def __init__(self, project_name: str):
        super().__init__(timeout=None)
        self.project_name = project_name

        db_cursor.execute("SELECT id, name FROM projects WHERE status = 'ativo'")

    async def initialize_session(self, interaction: discord.Interaction, selected_language: str):
        user_id = str(interaction.user.id)
        current_time = time.time()
        db_cursor.execute("INSERT INTO sessions (user_id, status, language, project_name, start_time, accumulated, ai_used, ai_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (user_id, 'ativo', selected_language, self.project_name, current_time, 0.0, '', ''))
        db_connection.commit()
        
        msg = (
            f"⏱️ Sessão iniciada no projeto **{self.project_name}** usando **{selected_language}**! Bons estudos!\n"
            f"💡 *Dica: Quer ver quanto tempo já passou sem parar o cronômetro? Use `/status` a qualquer momento!*"
        )
        await interaction.response.edit_message(content=msg, view=None)

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
        await interaction.response.edit_message(content=f"⏱️ Escolha a linguagem para o projeto **{self.project_name}**:", view=None)
        await interaction.followup.send_modal(CustomLanguageModal(self.project_name))

class ProjectSelectionView(discord.ui.View):
    def __init__(self, projects: list):
        super().__init__(timeout=None)
        # Adds buttons for each project found in database (up to 5)
        for proj in projects[:5]:
            proj_name = proj[1]
            btn = discord.ui.button(label=proj_name, emoji="📁", style=discord.ButtonStyle.secondary)
            async def callback(interaction: discord.Interaction, name=proj_name):
                await interaction.response.edit_message(content=f"📁 Projeto selecionado: **{name}**\n\nAgora, escolha a linguagem de programação:", view=LanguageSelectionView(name))
            btn.callback = callback
            self.add_item(btn)

    @discord.ui.button(label="Estudo Livre (Sem Projeto)", emoji="🚀", style=discord.ButtonStyle.primary, row=1)
    async def button_free_study(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="🚀 Modo **Estudo Livre** selecionado.\n\nAgora, escolha a linguagem de programação:", view=LanguageSelectionView("Estudo Livre"))

# ---------------------------------------------------------
# MODALS AND VIEWS FOR /STOP (AI SELECTION)
# ---------------------------------------------------------
class AITimeModal(discord.ui.Modal):
    ai_duration_input = discord.ui.TextInput(label='Tempo na IA? (em min)', required=True, placeholder="Ex: 15")

    def __init__(self, session_id: int, total_duration_seconds: float, session_language: str, ai_identifier: str, project_name: str):
        super().__init__(title=f'Uso do {ai_identifier}')
        self.session_id = session_id
        self.total_duration_seconds = total_duration_seconds
        self.session_language = session_language
        self.ai_identifier = ai_identifier
        self.project_name = project_name

    async def on_submit(self, interaction: discord.Interaction):
        ai_mins = self.ai_duration_input.value
        db_cursor.execute("UPDATE sessions SET status = 'finalizado', accumulated = ?, ai_used = ?, ai_time = ? WHERE id = ?", 
                       (self.total_duration_seconds, self.ai_identifier, ai_mins, self.session_id))
        db_connection.commit()
        
        minutes, seconds = divmod(int(round(self.total_duration_seconds)), 60)
        hours, minutes = divmod(minutes, 60)
        
        # Calculate AI percentage usage
        ai_secs = float(ai_mins) * 60 if ai_mins.isdigit() else 0.0
        ai_percentage = (ai_secs / self.total_duration_seconds) * 100 if self.total_duration_seconds > 0 else 0
        
        result_embed = discord.Embed(title="✅ Sessão Finalizada", color=discord.Color.green())
        result_embed.add_field(name="Projeto", value=self.project_name, inline=True)
        result_embed.add_field(name="Linguagem", value=self.session_language, inline=True)
        result_embed.add_field(name="Tempo Total", value=f"{hours}h {minutes}m {seconds}s", inline=True)
        result_embed.add_field(name="IA Utilizada", value=f"{self.ai_identifier} ({ai_mins} min - {ai_percentage:.1f}% do tempo)", inline=False)
        
        await interaction.response.edit_message(content=None, embed=result_embed, view=None)

class CustomAIModal(discord.ui.Modal, title='Qual IA você usou?'):
    custom_ai_input = discord.ui.TextInput(label='Nome da IA', required=True, placeholder="Ex: Tabnine, Llama...")
    ai_duration_input = discord.ui.TextInput(label='Tempo na IA? (em min)', required=True, placeholder="Ex: 15")

    def __init__(self, session_id: int, total_duration_seconds: float, session_language: str, project_name: str):
        super().__init__()
        self.session_id = session_id
        self.total_duration_seconds = total_duration_seconds
        self.session_language = session_language
        self.project_name = project_name

    async def on_submit(self, interaction: discord.Interaction):
        ai_mins = self.ai_duration_input.value
        ai_name = self.custom_ai_input.value
        db_cursor.execute("UPDATE sessions SET status = 'finalizado', accumulated = ?, ai_used = ?, ai_time = ? WHERE id = ?", 
                       (self.total_duration_seconds, ai_name, ai_mins, self.session_id))
        db_connection.commit()
        
        minutes, seconds = divmod(int(round(self.total_duration_seconds)), 60)
        hours, minutes = divmod(minutes, 60)
        
        ai_secs = float(ai_mins) * 60 if ai_mins.isdigit() else 0.0
        ai_percentage = (ai_secs / self.total_duration_seconds) * 100 if self.total_duration_seconds > 0 else 0
        
        result_embed = discord.Embed(title="✅ Sessão Finalizada", color=discord.Color.green())
        result_embed.add_field(name="Projeto", value=self.project_name, inline=True)
        result_embed.add_field(name="Linguagem", value=self.session_language, inline=True)
        result_embed.add_field(name="Tempo Total", value=f"{hours}h {minutes}m {seconds}s", inline=True)
        result_embed.add_field(name="IA Utilizada", value=f"{ai_name} ({ai_mins} min - {ai_percentage:.1f}% do tempo)", inline=False)
        
        await interaction.response.edit_message(content=None, embed=result_embed, view=None)

class StopSessionView(discord.ui.View):
    def __init__(self, session_id: int, total_duration_seconds: float, session_language: str, project_name: str):
        super().__init__(timeout=None)
        self.session_id = session_id
        self.total_duration_seconds = total_duration_seconds
        self.session_language = session_language
        self.project_name = project_name

    async def finalize_session_with_ai(self, interaction: discord.Interaction, selected_ai: str):
        await interaction.response.send_modal(AITimeModal(self.session_id, self.total_duration_seconds, self.session_language, selected_ai, self.project_name))

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
        await interaction.response.send_modal(CustomAIModal(self.session_id, self.total_duration_seconds, self.session_language, self.project_name))

    @discord.ui.button(label="Não usei IA", emoji="🚫", style=discord.ButtonStyle.danger, row=1)
    async def button_no_ai(self, interaction: discord.Interaction, button: discord.ui.Button):
        db_cursor.execute("UPDATE sessions SET status = 'finalizado', accumulated = ?, ai_used = 'Não', ai_time = '0' WHERE id = ?", 
                       (self.total_duration_seconds, self.session_id))
        db_connection.commit()

        minutes, seconds = divmod(int(round(self.total_duration_seconds)), 60)
        hours, minutes = divmod(minutes, 60)
        
        result_embed = discord.Embed(title="✅ Sessão Finalizada", color=discord.Color.green())
        result_embed.add_field(name="Projeto", value=self.project_name, inline=True)
        result_embed.add_field(name="Linguagem", value=self.session_language, inline=True)
        result_embed.add_field(name="Tempo Total", value=f"{hours}h {minutes}m {seconds}s", inline=True)
        result_embed.add_field(name="IA Utilizada", value="Nenhuma (0.0% do tempo) 🚫", inline=False)
        
        await interaction.response.edit_message(content=None, embed=result_embed, view=None)

# ---------------------------------------------------------
# SLASH COMMANDS (/)
# ---------------------------------------------------------
@bot_instance.tree.command(name="start", description="Começa a contar o tempo da sessão num projeto.")
async def command_start(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    db_cursor.execute("SELECT id FROM sessions WHERE user_id = ? AND status != 'finalizado'", (user_id,))
    if db_cursor.fetchone():
        await interaction.response.send_message("⚠️ Você já tem uma sessão em andamento! Use /stop ou /pause.", ephemeral=True)
        return
    
    # Fetch user projects
    db_cursor.execute("SELECT id, name FROM projects WHERE user_id = ? AND status = 'ativo'", (user_id,))
    user_projects = db_cursor.fetchall()
    
    await interaction.response.send_message("📁 **Qual projeto você vai focar agora?**", view=ProjectSelectionView(user_projects), ephemeral=False)

@bot_instance.tree.command(name="status", description="Mostra o andamento da sessão atual em tempo real.")
async def command_status(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    db_cursor.execute("SELECT status, language, project_name, start_time, accumulated FROM sessions WHERE user_id = ? AND status != 'finalizado'", (user_id,))
    session = db_cursor.fetchone()
    
    if not session:
        await interaction.response.send_message("❌ Você não tem nenhuma sessão em andamento no momento.", ephemeral=True)
        return
        
    status, language, project_name, start_time, accumulated = session
    
    current_duration = accumulated
    if status == 'ativo':
        current_duration += (time.time() - start_time)
        
    minutes, seconds = divmod(int(round(current_duration)), 60)
    hours, minutes = divmod(minutes, 60)
    
    status_icon = "▶️ Ativo" if status == 'ativo' else "⏸️ Pausado"
    
    status_embed = discord.Embed(title="⏱️ Status da Sessão Atual", color=discord.Color.blue())
    status_embed.add_field(name="Projeto", value=project_name or "Estudo Livre", inline=True)
    status_embed.add_field(name="Linguagem", value=language, inline=True)
    status_embed.add_field(name="Estado", value=status_icon, inline=True)
    status_embed.add_field(name="Tempo Decorrido", value=f"{hours}h {minutes}m {seconds}s", inline=False)
    
    await interaction.response.send_message(embed=status_embed, ephemeral=True)

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
    db_cursor.execute("SELECT id, language, project_name FROM sessions WHERE user_id = ? AND status = 'pausado'", (user_id,))
    paused_session = db_cursor.fetchone()
    if not paused_session:
        await interaction.response.send_message("❌ Você não tem nenhuma sessão pausada.", ephemeral=True)
        return
        
    session_id, session_language, project_name = paused_session
    db_cursor.execute("UPDATE sessions SET status = 'ativo', start_time = ? WHERE id = ?", (time.time(), session_id))
    db_connection.commit()
    await interaction.response.send_message(f"▶️ Sessão de **{session_language}** no projeto **{project_name}** retomada!", ephemeral=False)

@bot_instance.tree.command(name="stop", description="Finaliza a sessão atual.")
async def command_stop(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    db_cursor.execute("SELECT id, status, start_time, accumulated, language, project_name FROM sessions WHERE user_id = ? AND status != 'finalizado'", (user_id,))
    ongoing_session = db_cursor.fetchone()
    if not ongoing_session:
        await interaction.response.send_message("❌ Você não tem nenhuma sessão em andamento.", ephemeral=True)
        return
        
    session_id, session_status, start_time, accumulated_time, session_language, project_name = ongoing_session
    total_duration = accumulated_time
    if session_status == 'ativo':
        total_duration += (time.time() - start_time)
        
    await interaction.response.send_message(f"🛑 Sessão do projeto **{project_name}** pausada para finalização.\n\n**Qual IA você usou para te ajudar hoje?**", view=StopSessionView(session_id, total_duration, session_language, project_name), ephemeral=False)

@bot_instance.tree.command(name="ranking", description="Mostra o total de horas registradas na semana e uso de IA.")
async def command_ranking(interaction: discord.Interaction):
    current_date = datetime.datetime.now()
    start_of_week = (current_date - datetime.timedelta(days=current_date.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    
    db_cursor.execute("""
        SELECT user_id, SUM(accumulated) as total_time, SUM(CASE WHEN ai_time != '0' AND ai_time != '' THEN CAST(ai_time AS REAL) * 60 ELSE 0 END) as total_ai
        FROM sessions 
        WHERE status = 'finalizado' AND start_time >= ? 
        GROUP BY user_id 
        ORDER BY total_time DESC
    """, (start_of_week.timestamp(),))
    ranking_results = db_cursor.fetchall()

    if not ranking_results:
        await interaction.response.send_message("📊 Ainda não há horas registradas nesta semana. Bora codar!", ephemeral=False)
        return

    ranking_embed = discord.Embed(title="🏆 Ranking da Semana & Análise de IA", description="Total de tempo estudado e proporção de uso de Inteligência Artificial:", color=discord.Color.gold())
    
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
        user_id, total_seconds, total_ai_seconds = row
        total_seconds = total_seconds or 0
        total_ai_seconds = total_ai_seconds or 0
        
        minutes, seconds = divmod(int(round(total_seconds)), 60)
        hours, minutes = divmod(minutes, 60)
        
        ai_percentage = (total_ai_seconds / total_seconds) * 100 if total_seconds > 0 else 0
        
        medalha = medalhas[posicao - 1] if posicao <= 3 else "🏅"
        
        ranking_embed.add_field(
            name=f"{medalha} {posicao}º Lugar", 
            value=f"**Dev:** <@{user_id}>\n⏱️ **Tempo Total:** {hours}h {minutes}m {seconds}s\n🤖 **Dependência de IA:** {ai_percentage:.1f}% do tempo", 
            inline=False
        )
        posicao += 1

    await interaction.response.send_message(embed=ranking_embed)

# Project management group
project_group = app_commands.Group(name="project", description="Gerencie seus projetos de estudo.")

@project_group.command(name="create", description="Cria um novo projeto para focar seus estudos.")
@app_commands.describe(name="Nome do projeto (ex: MeuE-commerce, BotDiscord)")
async def project_create(interaction: discord.Interaction, name: str):
    user_id = str(interaction.user.id)
    db_cursor.execute("INSERT INTO projects (user_id, name, progress, status) VALUES (?, ?, 0, 'ativo')", (user_id, name))
    db_connection.commit()
    await interaction.response.send_message(f"📁 Projeto **{name}** criado com sucesso! Use `/start` para iniciar sessões nele.", ephemeral=True)

@project_group.command(name="progress", description="Atualiza a porcentagem de conclusão de um projeto.")
@app_commands.describe(name="Nome exato do projeto", percentage="Porcentagem de 0 a 100")
async def project_progress(interaction: discord.Interaction, name: str, percentage: int):
    if not (0 <= percentage <= 100):
        await interaction.response.send_message("⚠️ A porcentagem deve estar entre 0 e 100.", ephemeral=True)
        return
        
    user_id = str(interaction.user.id)
    db_cursor.execute("UPDATE projects SET progress = ? WHERE user_id = ? AND name = ?", (percentage, user_id, name))
    db_connection.commit()
    await interaction.response.send_message(f"📈 Projeto **{name}** atualizado para **{percentage}%** de conclusão!", ephemeral=False)

@project_group.command(name="list", description="Lista todos os seus projetos ativos e suas porcentagens.")
async def project_list(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    db_cursor.execute("SELECT name, progress FROM projects WHERE user_id = ? AND status = 'ativo'", (user_id,))
    projects = db_cursor.fetchall()
    
    if not projects:
        await interaction.response.send_message("📁 Você ainda não cadastrou nenhum projeto. Use `/project create` para criar um!", ephemeral=True)
        return
        
    embed = discord.Embed(title="📁 Seus Projetos Ativos", color=discord.Color.dark_purple())
    for name, progress in projects:
        # Progress bar visual helper
        filled_blocks = int(progress // 10)
        bar = "🟩" * filled_blocks + "⬜" * (10 - filled_blocks)
        embed.add_field(name=f"📌 {name}", value=f"Progresso: {progress}%\n{bar}", inline=False)
        
    await interaction.response.send_message(embed=embed, ephemeral=True)

bot_instance.tree.add_command(project_group)

# ---------------------------------------------------------
# INITIALIZATION
# ---------------------------------------------------------
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
bot_instance.run(DISCORD_TOKEN)