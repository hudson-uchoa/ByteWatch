import discord
from discord.ext import commands, tasks
from discord import app_commands
import datetime

# Configuração básica do Bot
class DevBot(commands.Bot):
    def __init__(self):
        # Intents básicos, não precisamos ler mensagens de texto se vamos usar só '/'
        super().__init__(command_prefix="!", intents=discord.Intents.default())

    async def setup_hook(self):
        # Sincroniza os comandos '/' com o servidor
        await self.tree.sync()
        # Inicia as tarefas automáticas em segundo plano
        self.check_timeouts.start()
        self.weekly_summary.start()

    # ---------------------------------------------------------
    # TAREFA: Auto-Stop de 2 Horas
    # ---------------------------------------------------------
    @tasks.loop(minutes=5)
    async def check_timeouts(self):
        # Lógica para checar no banco de dados se há sessões com status 'ativo' 
        # ou 'pausado' onde o (tempo atual - start_time) > 2 horas.
        # Se houver, atualiza o status para 'finalizado' automaticamente.
        pass

    # ---------------------------------------------------------
    # TAREFA: Resumo Semanal (Domingo às 14:00)
    # ---------------------------------------------------------
    @tasks.loop(minutes=1)
    async def weekly_summary(self):
        now = datetime.datetime.now()
        # Verifica se é Domingo (weekday() == 6) e se são 14:00
        if now.weekday() == 6 and now.hour == 14 and now.minute == 0:
            canal_registro = self.get_channel(SEU_ID_DO_CANAL_AQUI)
            # Lógica para somar os tempos da semana no banco de dados 
            # e enviar um Embed bonitão marcando você e a Ana.
            embed = discord.Embed(
                title="📊 Resumo Semanal de Código!",
                description="Olha o quanto nós codamos essa semana:",
                color=discord.Color.purple()
            )
            # Adicionar campos puxando do banco de dados...
            await canal_registro.send(embed=embed)

bot = DevBot()

# ---------------------------------------------------------
# COMANDOS SLASH (/)
# ---------------------------------------------------------

@bot.tree.command(name="start", description="Inicia o cronômetro de estudos.")
async def start(interaction: discord.Interaction):
    # Aqui você retornaria uma View com o Select Menu de linguagens.
    await interaction.response.send_message("⏱️ Cronômetro iniciado! Qual linguagem vamos estudar?", ephemeral=True)

@bot.tree.command(name="pause", description="Pausa a contagem atual.")
async def pause(interaction: discord.Interaction):
    # Salva o tempo decorrido no banco de dados.
    await interaction.response.send_message("⏸️ Tempo pausado. Pode ir tomar um café!", ephemeral=True)

# Modal (Pop-up) para o comando /stop
class IAFeedbackModal(discord.ui.Modal, title='Uso de Inteligência Artificial'):
    usou_ia = discord.ui.TextInput(label='Usou IA? (Sim/Não)', style=discord.TextStyle.short)
    qual_ia = discord.ui.TextInput(label='Qual IA? (ChatGPT, Gemini, etc)', required=False)
    tempo_ia = discord.ui.TextInput(label='Quanto tempo usou a IA? (em minutos)', required=False)

    async def on_submit(self, interaction: discord.Interaction):
        # Aqui você calcula o tempo total, salva as respostas da IA no banco 
        # e gera o sumário final da sessão.
        
        embed = discord.Embed(title="✅ Sessão Finalizada", color=discord.Color.green())
        embed.add_field(name="Tempo Total", value="1h 30m 15s", inline=False)
        embed.add_field(name="IA Utilizada", value=f"{self.qual_ia.value} ({self.tempo_ia.value} min)", inline=False)
        
        await interaction.response.send_message(embed=embed)

@bot.tree.command(name="stop", description="Para o cronômetro e finaliza a sessão.")
async def stop(interaction: discord.Interaction):
    # Abre o formulário (Modal) na tela de quem digitou o comando
    await interaction.response.send_modal(IAFeedbackModal())

bot.run('SEU_TOKEN_DO_DISCORD_AQUI')