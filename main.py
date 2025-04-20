import discord
from discord.ext import commands
from discord import app_commands
from myserver import server_on
import json
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
bot.user_bag = {}
bot.user_team = {}

item_emojis = {
    "Pokeball": "<:emoji_4:1361942448514797570>",
    "Revive": "<:emoji_3:1361905327741603890>"
}

item_choices = [
    app_commands.Choice(name="Pokeball", value="Pokeball"),
    app_commands.Choice(name="Revive", value="Revive"),
]

def save_data():
    with open("bag_data.json", "w") as f:
        json.dump(bot.user_bag, f)
    with open("team_data.json", "w") as f:
        json.dump(bot.user_team, f)

def load_data():
    if os.path.exists("bag_data.json"):
        with open("bag_data.json", "r") as f:
            bot.user_bag = json.load(f)
    if os.path.exists("team_data.json"):
        with open("team_data.json", "r") as f:
            bot.user_team = json.load(f)

@bot.event
async def on_ready():
    load_data()
    print("Bot online!")
    await bot.tree.sync()
    print("Command tree synced!")

@bot.tree.command(name="ping", description="Pong!")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")

@bot.tree.command(name="additem", description="เพิ่ม item ในกระเป๋า (เฉพาะแอดมิน)")
@app_commands.describe(user="ผู้ที่จะได้รับของ", item="ชื่อของ", amount="จำนวน")
@app_commands.choices(item=item_choices)
async def additem(interaction: discord.Interaction, user: discord.User, item: app_commands.Choice[str], amount: int):
    if not any(role.name == "Admin" for role in interaction.user.roles):
        await interaction.response.send_message(
            embed=discord.Embed(description="คุณไม่มีสิทธิ์ใช้คำสั่งนี้", color=discord.Color.red()),
            ephemeral=True
        )
        return

    user_id = str(user.id)
    item_name = item.value
    emoji = item_emojis.get(item_name, "")

    if user_id not in bot.user_bag:
        bot.user_bag[user_id] = {}

    if item_name in bot.user_bag[user_id]:
        bot.user_bag[user_id][item_name] += amount
    else:
        bot.user_bag[user_id][item_name] = amount

    await interaction.response.send_message(
        embed=discord.Embed(
            description=f"เพิ่ม {emoji} **{item_name}** จำนวน **{amount}** ให้กับ {user.mention}",
            color=discord.Color.green()
        )
    )
    save_data()

@bot.tree.command(name="bag", description="ดูของในกระเป๋า")
async def bag(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    bag = bot.user_bag.get(user_id, {})

    if not bag:
        await interaction.response.send_message(
            embed=discord.Embed(description="ไม่มี item ในกระเป๋า", color=discord.Color.orange()),
            ephemeral=True
        )
        return

    bag_items = "\n".join([
        f"{item_emojis.get(item, '')} • **{item}** × {amount}"
        for item, amount in bag.items()
    ])

    await interaction.response.send_message(
        embed=discord.Embed(
            title=f"{interaction.user.name}'s Bag 🎒",
            description=bag_items,
            color=discord.Color.blue()
        )
    )

@bot.tree.command(name="unlock", description="จับตัวเลขและชื่อด้วย Pokeball")
@app_commands.describe(number="เลขโปเกม่อน", name="ชื่อโปเกม่อน")
async def unlock(interaction: discord.Interaction, number: int, name: str):
    user_id = str(interaction.user.id)
    bag = bot.user_bag.get(user_id, {})

    if bag.get("Pokeball", 0) < 1:
        await interaction.response.send_message(
            embed=discord.Embed(description="คุณไม่มี Pokeball ในกระเป๋า!", color=discord.Color.red()),
            ephemeral=True
        )
        return

    bot.user_bag[user_id]["Pokeball"] -= 1

    if user_id not in bot.user_team:
        bot.user_team[user_id] = []

    bot.user_team[user_id].append((number, name, False))

    await interaction.response.send_message(
        embed=discord.Embed(
            description=f"เพิ่ม **{number}** ชื่อ **{name}** เรียบร้อย! (-1 Pokeball)",
            color=discord.Color.green()
        )
    )
    save_data()

@bot.tree.command(name="team", description="ดูโปเกม่อนของคุณในทีม")
async def team(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    team = bot.user_team.get(user_id, [])

    if not team:
        await interaction.response.send_message(
            embed=discord.Embed(description="คุณยังไม่มีโปเกม่อนในทีมเลย", color=discord.Color.orange()),
            ephemeral=True
        )
        return

    team_text = ""
    for i, (number, name, is_rip) in enumerate(team, start=1):
        emoji = "🔴" if is_rip else "🟢"
        team_text += f"{emoji} `{i}` • ``{number}`` : {name}\n"

    await interaction.response.send_message(
        embed=discord.Embed(
            title=f"{interaction.user.name}'s Team <:emoji_4:1361942448514797570>",
            description=team_text,
            color=discord.Color.purple()
        )
    )

@bot.tree.command(name="teamof", description="ดูทีมของผู้ใช้อื่น (เฉพาะแอดมิน)")
@app_commands.describe(user="ผู้ใช้ที่ต้องการดูทีม")
async def teamof(interaction: discord.Interaction, user: discord.User):
    if not any(role.name == "Admin" for role in interaction.user.roles):
        await interaction.response.send_message(
            embed=discord.Embed(description="คุณไม่มีสิทธิ์ดูทีมของคนอื่น", color=discord.Color.red()),
            ephemeral=True
        )
        return

    user_id = str(user.id)
    team = bot.user_team.get(user_id, [])

    if not team:
        await interaction.response.send_message(
            embed=discord.Embed(description=f"{user.name} ยังไม่มีสมาชิกในทีม", color=discord.Color.orange()),
            ephemeral=True
        )
        return

    team_text = ""
    for i, (number, name, is_rip) in enumerate(team, start=1):
        emoji = "🔴" if is_rip else "🟢"
        team_text += f"{emoji} **{i}.** เลข: `{number}` ชื่อ: **{name}**\n"

    await interaction.response.send_message(
        embed=discord.Embed(
            title=f"Team ของ {user.name}",
            description=team_text,
            color=discord.Color.purple()
        )
    )

@bot.tree.command(name="removeteam", description="ลบสมาชิกในทีมของผู้ใช้ (เฉพาะแอดมิน)")
@app_commands.describe(user="ผู้ใช้ที่ต้องการลบ", index="ลำดับของสมาชิกในทีม (เริ่มที่ 1)")
async def removeteam(interaction: discord.Interaction, user: discord.User, index: int):
    if not any(role.name == "Admin" for role in interaction.user.roles):
        await interaction.response.send_message(
            embed=discord.Embed(description="คุณไม่มีสิทธิ์ลบทีมของคนอื่น", color=discord.Color.red()),
            ephemeral=True
        )
        return

    user_id = str(user.id)
    team = bot.user_team.get(user_id, [])

    if not team:
        await interaction.response.send_message(
            embed=discord.Embed(description=f"{user.name} ยังไม่มีทีม", color=discord.Color.orange()),
            ephemeral=True
        )
        return

    if index < 1 or index > len(team):
        await interaction.response.send_message(
            embed=discord.Embed(description="ลำดับไม่ถูกต้อง", color=discord.Color.orange()),
            ephemeral=True
        )
        return

    removed = team.pop(index - 1)
    await interaction.response.send_message(
        embed=discord.Embed(
            description=f"ลบโปเกม่อนหมายเลข `{removed[0]}` ชื่อ **{removed[1]}** จากทีมของ {user.name} แล้ว",
            color=discord.Color.green()
        )
    )
    save_data()

@bot.tree.command(name="rip", description="เพิ่มเลขโปเกม่อนที่ตาย (เฉพาะแอดมิน)")
@app_commands.describe(user="ผู้ใช้", index="ลำดับของสมาชิกในทีม (เริ่มที่ 1)")
async def rip(interaction: discord.Interaction, user: discord.User, index: int):
    if not any(role.name == "Admin" for role in interaction.user.roles):
        await interaction.response.send_message(
            embed=discord.Embed(description="คุณไม่มีสิทธิ์ใช้คำสั่งนี้", color=discord.Color.red()),
            ephemeral=True
        )
        return

    user_id = str(user.id)
    team = bot.user_team.get(user_id, [])
    if not team:
        await interaction.response.send_message(
            embed=discord.Embed(description="ทีมของผู้ใช้นี้ว่างเปล่า", color=discord.Color.orange()),
            ephemeral=True
        )
        return

    if index < 1 or index > len(team):
        await interaction.response.send_message(
            embed=discord.Embed(description="ลำดับไม่ถูกต้อง", color=discord.Color.orange()),
            ephemeral=True
        )
        return

    number, name, _ = team[index - 1]
    team[index - 1] = (number, name, True)

    await interaction.response.send_message(
        embed=discord.Embed(
            description=f"ตั้งค่า 🔴 ให้กับ `{number}` : **{name}** ในทีมของ {user.mention}",
            color=discord.Color.red()
        )
    )
    save_data()

@bot.tree.command(name="revive", description="ชุบชีวิตสมาชิกในทีมของคุณ โดยใช้ไอเท็ม Revive")
@app_commands.describe(index="ลำดับของสมาชิกในทีม (เริ่มที่ 1)")
async def revive(interaction: discord.Interaction, index: int):
    user = interaction.user
    user_id = str(user.id)
    team = bot.user_team.get(user_id, [])
    bag = bot.user_bag.get(user_id, {})

    if not team:
        await interaction.response.send_message(
            embed=discord.Embed(description="คุณยังไม่มีทีม", color=discord.Color.orange()),
            ephemeral=True
        )
        return

    if index < 1 or index > len(team):
        await interaction.response.send_message(
            embed=discord.Embed(description="ลำดับไม่ถูกต้อง", color=discord.Color.orange()),
            ephemeral=True
        )
        return

    if bag.get("Revive", 0) < 1:
        await interaction.response.send_message(
            embed=discord.Embed(description="คุณไม่มีไอเท็ม Revive!", color=discord.Color.red()),
            ephemeral=True
        )
        return

    bot.user_bag[user_id]["Revive"] -= 1

    number, name, _ = team[index - 1]
    team[index - 1] = (number, name, False)

    await interaction.response.send_message(
        embed=discord.Embed(
            description=f"โปเกม่อนหมายเลข `{number}` ชื่อ **{name}** ของคุณฟื้นแล้ว! (🟢) (-1 Revive)",
            color=discord.Color.green()
        )
    )
    save_data()

@bot.tree.command(name="help", description="ดูคำสั่งทั้งหมด")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="คำสั่งทั้งหมด",
        description=(
            "- `/bag ดูของในกระเป๋า`\n"
            "- `/team ดูโปเกม่อนของคุณในทีม`\n"
            "- `/unlock ปลดล็อคโปเกม่อนด้วย pokeball`\n"
            "- `/revive ชุบชีวิตโปเกม่อนด้วย revive`"
        )
    )
    await interaction.response.send_message(embed=embed)

TOKEN = os.getenv('DISCORD_TOKEN')

server_on ()

bot.run(TOKEN)