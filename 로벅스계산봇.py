import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from enum import Enum

BOT_TOKEN = '디코봇넣기'
로벅스_가격_단위 = 10000 #1000로벅스당 원화 가격
DATA_FILE = 'guild_data.json'

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)
guild_settings = {}

def load_data():
    global guild_settings
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                guild_settings = json.load(f)
        except Exception as e:
            print(f"❌ 데이터 불러오기 실패: {e}")
            guild_settings = {}
    else:
        guild_settings = {}

def save_data():
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(guild_settings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ 데이터 저장 실패: {e}")

def get_guild_settings(guild: discord.Guild):
    guild_id = str(guild.id)
    if guild_id not in guild_settings:
        guild_settings[guild_id] = {
            "guild_name": guild.name,
            "stock": 0,
            "count_per_unit": 0,
            "price_unit": 로벅스_가격_단위,
            "live_channel_id": None,
            "live_message_id": None
        }
        save_data()
    return guild_settings[guild_id]

def build_live_embed(guild: discord.Guild) -> discord.Embed:
    s = get_guild_settings(guild)
    unit = s.get("price_unit", 로벅스_가격_단위)
    count = s.get("count_per_unit", 0)
    stock = s.get("stock", 0)
    embed = discord.Embed(
        title=f"{guild.name} 로벅스 실시간 정보",
        description=f"재고: **{stock}**개\n가격: **{unit}원 당 {count} 로벅스**",
        color=discord.Color.blurple()
    )
    return embed

class CalcView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="원화로 계산", style=discord.ButtonStyle.green, custom_id="calc_won")
    async def calc_won(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(WonInputModal())

    @discord.ui.button(label="로벅스로 계산", style=discord.ButtonStyle.primary, custom_id="calc_robux")
    async def calc_robux(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RobuxInputModal())

class WonInputModal(discord.ui.Modal, title="원화로 계산"):
    amount: discord.ui.TextInput = discord.ui.TextInput(label="금액(원)", placeholder="예: 9000", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            won = int(str(self.amount.value).strip())
        except Exception:
            embed = discord.Embed(description="❌ 정수를 입력해주세요.", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        s = get_guild_settings(interaction.guild)
        unit = s.get("price_unit", 로벅스_가격_단위)
        count = s.get("count_per_unit", 0)
        if unit <= 0 or count <= 0:
            embed = discord.Embed(description="❌ 가격 단위 또는 로벅스 개수가 설정되지 않았습니다.", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        robux = int((won / unit) * count)
        embed = discord.Embed(description=f"✅ {won}원 ⇒ 약 **{robux} 로벅스**", color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)

class RobuxInputModal(discord.ui.Modal, title="로벅스로 계산"):
    amount: discord.ui.TextInput = discord.ui.TextInput(label="로벅스 개수", placeholder="예: 900", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            rbx = int(str(self.amount.value).strip())
        except Exception:
            embed = discord.Embed(description="❌ 정수를 입력해주세요.", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        s = get_guild_settings(interaction.guild)
        unit = s.get("price_unit", 로벅스_가격_단위)
        count = s.get("count_per_unit", 0)
        if unit <= 0 or count <= 0:
            embed = discord.Embed(description="❌ 가격 단위 또는 로벅스 개수가 설정되지 않았습니다.", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        won = int((rbx / count) * unit)
        embed = discord.Embed(description=f"✅ {rbx} 로벅스 ⇒ 약 **{won}원**", color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def update_live_message(guild: discord.Guild):
    s = get_guild_settings(guild)
    channel_id = s.get("live_channel_id")
    message_id = s.get("live_message_id")
    if not channel_id or not message_id:
        return
    channel = guild.get_channel(int(channel_id))
    if channel is None:
        return
    try:
        msg = await channel.fetch_message(int(message_id))
        await msg.edit(embed=build_live_embed(guild), view=CalcView())
    except Exception as e:
        print(f"❗ 실시간 메시지 업데이트 실패: {e}")

@bot.event
async def on_ready():
    load_data()
    print(f'{bot.user.name} 봇이 시작되었습니다!')
    print(f'봇 초대 링크: https://discord.com/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot')
    print("❗ 로벅스 재고 관리 및 가격 설정 명령어는 서버 관리자만 사용할 수 있습니다.")
    print("💾 설정은 서버별로 자동 저장되며, 봇 재시작 후에도 유지됩니다.")

    for guild in bot.guilds:
        get_guild_settings(guild)
    try:
        bot.add_view(CalcView())
    except Exception as e:
        print(f"❌ 뷰 등록 실패: {e}")

    print("⏳ 슬래시 명령어 동기화 중...")
    try:
        synced = await bot.tree.sync()
        print(f"✅ 슬래시 명령어 동기화 완료! {len(synced)}개 명령어가 등록되었습니다.")
    except Exception as e:
        print(f"❌ 슬래시 명령어 동기화 중 오류 발생: {e}")

@bot.event
async def on_guild_join(guild: discord.Guild):
    get_guild_settings(guild)
    print(f"➕ 새 서버 참여: {guild.name} ({guild.id}) 데이터 초기화 완료")

class StockAction(Enum):
    추가 = "add"
    제거 = "remove"

@bot.tree.command(name="재고관리", description="로벅스 재고를 추가 또는 제거합니다 (관리자 전용).")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(
    동작="추가 또는 제거 중에서 선택",
    개수="증감할 로벅스 개수 (정수)"
)
@app_commands.choices(동작=[
    app_commands.Choice(name="추가", value="add"),
    app_commands.Choice(name="제거", value="remove")
])
async def 재고관리_슬래시(interaction: discord.Interaction, 동작: app_commands.Choice[str], 개수: int):
    if 개수 <= 0:
        embed = discord.Embed(description="❌ 개수는 1 이상의 정수여야 합니다.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    s = get_guild_settings(interaction.guild)
    before = int(s.get("stock", 0))
    if 동작.value == "add":
        s["stock"] = before + 개수
        action_text = "추가"
    else:
        s["stock"] = max(0, before - 개수)
        action_text = "제거"
    guild_settings[str(interaction.guild.id)] = s
    save_data()
    after = s["stock"]
    embed = discord.Embed(description=f"✅ 재고 {action_text} 완료: **{개수}개**\n현재 재고: **{after}개**", color=discord.Color.green())
    await interaction.response.send_message(embed=embed, ephemeral=True)
    await update_live_message(interaction.guild)

@bot.tree.command(name="로벅스재고관리", description="로벅스 재고를 추가합니다 (관리자 전용).")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(
    추가할_개수="추가할 로벅스 개수 (정수)"
)
async def 로벅스재고관리_슬래시(interaction: discord.Interaction, 추가할_개수: int):
    if 추가할_개수 < 0:
        await interaction.response.send_message("❌ 추가할 개수는 0 이상의 정수여야 합니다.", ephemeral=True)
        return

    settings = get_guild_settings(interaction.guild)
    settings["stock"] = int(settings.get("stock", 0)) + 추가할_개수
    guild_settings[str(interaction.guild.id)] = settings
    save_data()
    embed = discord.Embed(description=f"✅ 로벅스 재고 {추가할_개수}개가 추가되었습니다.\n현재 재고: **{settings['stock']}개**", color=discord.Color.green())
    await interaction.response.send_message(embed=embed, ephemeral=True)
    await update_live_message(interaction.guild)

@로벅스재고관리_슬래시.error
async def 로벅스재고관리_슬래시_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        embed = discord.Embed(description="❌ 이 명령어는 서버 관리자만 사용할 수 있습니다.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        print(f"로벅스재고관리 명령어 에러 발생: {error}")
        embed = discord.Embed(description="❌ 오류가 발생했습니다. 개발자에게 문의해주세요.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="로벅스재고", description="현재 로벅스 재고를 확인합니다.")
async def 로벅스재고_슬래시(interaction: discord.Interaction):
    settings = get_guild_settings(interaction.guild)
    embed = discord.Embed(description=f"현재 로벅스 재고는 **{settings['stock']}**개 입니다!", color=discord.Color.green())
    await interaction.response.send_message(embed=embed, ephemeral=True)

@로벅스재고_슬래시.error
async def 로벅스재고_슬래시_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    print(f"로벅스재고 명령어 에러 발생: {error}")
    embed = discord.Embed(description="❌ 오류가 발생했습니다. 개발자에게 문의해주세요.", color=discord.Color.red())
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="로벅스가격관리", description="지정된 가격 단위당 로벅스 개수를 설정합니다 (관리자 전용).")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(
    개수="10000원 당 로벅스 개수 (정수)"
)
async def 로벅스가격관리_슬래시(interaction: discord.Interaction, 개수: int):
    if 개수 < 0:
        await interaction.response.send_message("❌ 개수는 0 이상의 정수여야 합니다.", ephemeral=True)
        return

    settings = get_guild_settings(interaction.guild)
    settings["count_per_unit"] = 개수
    guild_settings[str(interaction.guild.id)] = settings
    save_data()
    embed = discord.Embed(description=f"✅ 단위당 로벅스 개수가 **{settings['count_per_unit']}개**로 설정되었습니다.\n가격 단위: **{settings.get('price_unit', 로벅스_가격_단위)}원**", color=discord.Color.green())
    await interaction.response.send_message(embed=embed, ephemeral=True)
    await update_live_message(interaction.guild)

@bot.tree.command(name="로벅스단위", description="가격 단위(원)와 해당 로벅스 개수를 설정합니다 (관리자 전용).")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(
    가격_단위="가격 단위 (예: 10000)",
    개수="가격 단위당 로벅스 개수 (예: 1200)"
)
async def 로벅스단위_슬래시(interaction: discord.Interaction, 가격_단위: int, 개수: int):
    if 가격_단위 <= 0 or 개수 < 0:
        embed = discord.Embed(description="❌ 가격 단위는 1 이상, 개수는 0 이상이어야 합니다.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    s = get_guild_settings(interaction.guild)
    s["price_unit"] = 가격_단위
    s["count_per_unit"] = 개수
    guild_settings[str(interaction.guild.id)] = s
    save_data()
    embed = discord.Embed(description=f"✅ 단위 설정 완료: **{가격_단위}원** 당 **{개수} 로벅스**", color=discord.Color.green())
    await interaction.response.send_message(embed=embed, ephemeral=True)
    await update_live_message(interaction.guild)

@bot.tree.command(name="가격관리", description="가격 단위(원)와 로벅스 개수를 한 번에 설정합니다 (관리자 전용).")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(
    가격_단위="가격 단위 (예: 10000)",
    개수="가격 단위당 로벅스 개수 (예: 1200)"
)
async def 가격관리_슬래시(interaction: discord.Interaction, 가격_단위: int, 개수: int):
    if 가격_단위 <= 0 or 개수 < 0:
        embed = discord.Embed(description="❌ 가격 단위는 1 이상, 개수는 0 이상이어야 합니다.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    s = get_guild_settings(interaction.guild)
    s["price_unit"] = 가격_단위
    s["count_per_unit"] = 개수
    guild_settings[str(interaction.guild.id)] = s
    save_data()
    embed = discord.Embed(description=f"✅ 가격 설정이 업데이트되었습니다.\n- 가격 단위: **{가격_단위}원**\n- 로벅스 개수: **{개수}개** (단위당)", color=discord.Color.green())
    await interaction.response.send_message(embed=embed, ephemeral=True)
    await update_live_message(interaction.guild)

@bot.tree.command(name="로벅스실시간재고채널", description="실시간 재고 임베드를 설정할 채널을 지정합니다 (관리자 전용).")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(
    채널="임베드를 게시할 텍스트 채널"
)
async def 로벅스실시간재고채널_슬래시(interaction: discord.Interaction, 채널: discord.TextChannel):
    s = get_guild_settings(interaction.guild)
    try:
        msg = await 채널.send(embed=build_live_embed(interaction.guild), view=CalcView())
        s["live_channel_id"] = 채널.id
        s["live_message_id"] = msg.id
        guild_settings[str(interaction.guild.id)] = s
        save_data()
        embed = discord.Embed(description=f"✅ 실시간 재고 채널 설정 완료: {채널.mention}", color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        embed = discord.Embed(description=f"❌ 메시지 전송 실패: {e}", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)

@로벅스가격관리_슬래시.error
async def 로벅스가격관리_슬래시_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        embed = discord.Embed(description="❌ 이 명령어는 서버 관리자만 사용할 수 있습니다.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        print(f"로벅스가격관리 명령어 에러 발생: {error}")
        embed = discord.Embed(description="❌ 오류가 발생했습니다. 개발자에게 문의해주세요.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="로벅스계산기", description="원하는 금액의 로벅스 개수를 계산합니다.")
@app_commands.describe(
    금액="로벅스로 계산할 금액 (정수)"
)
async def 로벅스계산기_슬래시(interaction: discord.Interaction, 금액: int):
    if 금액 < 0:
        embed = discord.Embed(description="❌ 금액은 0 이상의 정수여야 합니다.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    settings = get_guild_settings(interaction.guild)
    if settings.get("count_per_unit", 0) <= 0:
        embed = discord.Embed(description=f"❌ {settings.get('price_unit', 로벅스_가격_단위)}원 당 로벅스 개수가 설정되지 않았거나 0입니다. 관리자에게 문의해주세요.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    unit = settings.get("price_unit", 로벅스_가격_단위)
    계산된_로벅스 = (금액 / unit) * settings["count_per_unit"]
    계산된_로벅스 = int(계산된_로벅스)

    embed = discord.Embed(description=f"**{금액}**원의 로벅스 양은 **{계산된_로벅스}**입니다!", color=discord.Color.green())
    await interaction.response.send_message(embed=embed, ephemeral=True)

@로벅스계산기_슬래시.error
async def 로벅스계산기_슬래시_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    print(f"로벅스계산기 명령어 에러 발생: {error}")
    embed = discord.Embed(description="❌ 오류가 발생했습니다. 개발자에게 문의해주세요.", color=discord.Color.red())
    await interaction.response.send_message(embed=embed, ephemeral=True)

bot.run(BOT_TOKEN)

