import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import requests

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = discord.Object(id=1330840445869228032)

github_org = "tagglabs"
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def github_api_request(endpoint: str, method: str = "GET", data: dict = None):
    url = f"https://api.github.com{endpoint}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    response = requests.request(method, url, headers=headers, json=data)
    response.raise_for_status()
    if response.headers.get("content-type") == "application/json; charset=utf-8":
        return response.json()

class CreateRepoModal(discord.ui.Modal, title="Create New Repository"):
    repo_name = discord.ui.TextInput(
        label="Repository Name",
        placeholder="Enter repository name",
        max_length=100,
    )
    description = discord.ui.TextInput(
        label="Description",
        placeholder="Enter repository description",
        style=discord.TextStyle.long,
        required=False,
        max_length=500,
    )
    visibility = discord.ui.TextInput(
        label="Visibility (public/private)",
        placeholder="public or private",
        required=False,
        max_length=7,
    )
    initialize_readme = discord.ui.TextInput(
        label="Initialize with README (yes/no)",
        placeholder="yes or no",
        required=False,
        max_length=3,
    )

    async def on_submit(self, interaction: discord.Interaction):
        repo_name = self.repo_name.value
        description = self.description.value or ""
        visibility = self.visibility.value.lower() or "public"
        initialize_readme = self.initialize_readme.value.lower() == "yes"

        data = {
            "name": repo_name,
            "description": description,
            "private": visibility == "private",
            "has_projects": True,
            "auto_init": initialize_readme,
            "gitignore_template": "Python",
            "license_template": "mit",
        }
        try:
            repo = github_api_request(f"/orgs/{github_org}/repos", method="POST", data=data)
            team_repo_data = {
            'permission': 'maintain'
            }
            #/orgs/{org}/teams/{team_slug}/repos/{owner}/{repo}
            github_api_request(f'/orgs/{github_org}/teams/campaigns/repos/{github_org}/{repo_name}', method='PUT', data=team_repo_data)
            await interaction.response.send_message(
                f"Repository '{repo_name}' created successfully: {repo['html_url']}"
            )
        except requests.exceptions.RequestException as e:
            await interaction.response.send_message(
                f"Failed to create repository: {e}", ephemeral=True
            )

@bot.event
async def on_ready():
    print(f"Bot is ready and logged in as {bot.user}.")
    global_sync = await bot.tree.sync()
    print(f"Bot synced globally with {len(global_sync)} commands.")
    bot.tree.copy_global_to(guild=GUILD_ID)
    guild_sync = await bot.tree.sync(guild=GUILD_ID)
    print(f"Bot with {len(guild_sync)} commands on {GUILD_ID.id}.")

@bot.tree.command(name="create_repo")
async def create_repo(interaction: discord.Interaction):
    """Open a form modal to create a new repository."""
    await interaction.response.send_modal(CreateRepoModal())

bot.run(DISCORD_TOKEN)
