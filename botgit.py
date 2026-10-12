
import os
import re
import base64
import requests
import discord
from discord.ext import commands

# =========================
# CONFIGURAÇÃO
# =========================

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

REPO_OWNER = "gaga123308"
REPO_NAME = "Usu-rios-Drak-hub"
FILE_PATH = "User.lua"
BRANCH = "main"

ROLES = {
    "moderador": "Moderador",
    "admin": "Admin",
    "dono": "Dono",
    "sub dono": "Sub dono",
    "yt": "yt",
    "staff": "Staff",
}

if not DISCORD_TOKEN or not GITHUB_TOKEN or OWNER_ID == 0:
    raise RuntimeError(
        "Configure DISCORD_TOKEN, GITHUB_TOKEN e OWNER_ID."
    )

# =========================
# DISCORD
# =========================

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# GITHUB
# =========================

API_URL = (
    f"https://api.github.com/repos/{REPO_OWNER}/"
    f"{REPO_NAME}/contents/{FILE_PATH}"
)

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

def github_request():
    response = requests.get(
        API_URL,
        headers=HEADERS,
        params={"ref": BRANCH},
        timeout=20,
    )
    response.raise_for_status()

    data = response.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    return content, data["sha"]


def parse_users(lua_code):
    # Lê entradas no formato ["usuario"] = "cargo"
    pattern = r'\["([^"]*)"\]\s*=\s*"([^"]*)"'
    users = {}

    for username, role in re.findall(pattern, lua_code):
        if username:
            users[username] = role

    return users


def save_users(users, sha):
    lines = ["return {"]

    for username, role in users.items():
        # Impede caracteres que poderiam quebrar a sintaxe Lua.
        username = username.replace("\\", "\\\\").replace('"', '\\"')
        role = role.replace("\\", "\\\\").replace('"', '\\"')

        lines.append(f'    ["{username}"] = "{role}",')

    lines.append("}")
    new_content = "\n".join(lines) + "\n"

    encoded = base64.b64encode(
        new_content.encode("utf-8")
    ).decode("ascii")

    response = requests.put(
        API_URL,
        headers=HEADERS,
        json={
            "message": "Atualiza lista de usuários do Drak Hub",
            "content": encoded,
            "sha": sha,
            "branch": BRANCH,
        },
        timeout=20,
    )
    response.raise_for_status()


# =========================
# COMANDO USERLIST
# =========================

@bot.command(name="userlist")
async def userlist(ctx, username: str = None, *, role: str = None):

    # Somente o proprietário autorizado pode alterar o arquivo.
    if ctx.author.id != OWNER_ID:
        await ctx.reply("❌ Tu não tens autorização para usar esse comando.")
        return

    if not username or not role:
        await ctx.reply(
            "Uso: `!userlist NomeDoRoblox Cargo`\n"
            "Cargos: Moderador, Admin, Dono, Sub Dono, YT ou Staff."
        )
        return

    role_key = role.strip().lower()

    if role_key not in ROLES:
        await ctx.reply(
            "❌ Cargo inválido. Usa: Moderador, Admin, Dono, "
            "Sub Dono, YT ou Staff."
        )
        return

    if not re.fullmatch(r"[A-Za-z0-9_]{1,20}", username):
        await ctx.reply("❌ Nome inválido. Confere o nome do Roblox.")
        return

    await ctx.reply("⏳ Atualizando o User.lua...")

    try:
        lua_code, sha = github_request()
        users = parse_users(lua_code)

        # Atualiza o cargo se o usuário já existir.
        users[username] = ROLES[role_key]

        save_users(users, sha)

        await ctx.send(
            f"✅ **User.lua atualizado!**\n"
            f"👤 Usuário: `{username}`\n"
            f"🏷️ Cargo: `{ROLES[role_key]}`\n"
            f"📁 Repositório: "
            f"https://github.com/{REPO_OWNER}/{REPO_NAME}/blob/"
            f"{BRANCH}/{FILE_PATH}"
        )

    except requests.RequestException:
        await ctx.send(
            "❌ Não consegui atualizar o GitHub. "
            "Confere as permissões do token e tenta novamente."
        )
    except Exception:
        await ctx.send("❌ Ocorreu um erro ao processar o arquivo.")


@bot.event
async def on_ready():
    print(f"Bot conectado: {bot.user}")


bot.run(DISCORD_TOKEN)

