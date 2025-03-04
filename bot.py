import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import os
import requests


load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = discord.Object(id=1330840445869228032)

github_org = "tagglabs"
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)


# GitHub API request function
async def github_api_request(endpoint: str, method: str = "GET", data: dict = None):
    url = f"https://api.github.com{endpoint}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    response = requests.request(method, url, headers=headers, json=data)
    if response.status_code == 403:
        raise PermissionError(
            "Access forbidden: Check your token permissions and repository access."
        )
    response.raise_for_status()
    if response.headers.get("content-type") == "application/json; charset=utf-8":
        return response.json()


# ---------- Modal for Creating a Repository ----------
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

    async def on_submit(self, interaction: discord.Interaction):
        repo_name = self.repo_name.value
        description = self.description.value or ""
        visibility = self.visibility.value.lower() or "public"
        is_private = visibility == "private"

        data = {
            "owner": github_org,
            "name": repo_name,
            "description": description,
            "private": is_private,
        }

        try:
            repo = await github_api_request(
                "/repos/tagglabs/precommit-config/generate",
                method="POST",
                data=data,
            )

            team_repo_data = {"permission": "maintain"}
            await github_api_request(
                f"/orgs/{github_org}/teams/campaigns/repos/{github_org}/{repo_name}",
                method="PUT",
                data=team_repo_data,
            )
            await interaction.response.send_message(
                f"Repository '{repo_name}' created successfully: {repo['html_url']}"
            )
        except requests.exceptions.RequestException as e:
            await interaction.response.send_message(
                f"Failed to create repository: {e}", ephemeral=True
            )


# ---------- Modal for Searching Repositories ----------
class SearchReposModal(discord.ui.Modal, title="Search Repositories"):
    search_term = discord.ui.TextInput(
        label="Search Term",
        placeholder="Enter keywords...",
        max_length=100,
    )

    async def on_submit(self, interaction: discord.Interaction):
        search_term = self.search_term.value
        try:
            repos = await github_api_request(
                f"/search/repositories?q={search_term}+org:{github_org}"
            )
            if repos.get("items"):
                repo_list = "\n".join(
                    f"- [{repo['name']}]({repo['html_url']})"
                    for repo in repos["items"][:5]
                )
                await interaction.response.send_message(
                    f"🔍 **Search Results:**\n{repo_list}"
                )
            else:
                await interaction.response.send_message(
                    "No repositories found.", ephemeral=True
                )
        except requests.exceptions.RequestException as e:
            await interaction.response.send_message(
                f"Failed to search repositories: {e}", ephemeral=True
            )


# ---------- Slash Commands ----------
@bot.tree.command(
    name="list_repos", description="List all repositories in the GitHub organization"
)
async def list_repos(interaction: discord.Interaction):
    """Lists all repositories in the GitHub organization."""
    try:
        repos = await github_api_request(f"/orgs/{github_org}/repos")
        repo_list = "\n".join(
            f"- [{repo['name']}]({repo['html_url']})" for repo in repos[:10]
        )
        await interaction.response.send_message(f"📂 **Repositories:**\n{repo_list}")
    except requests.exceptions.RequestException as e:
        await interaction.response.send_message(
            f"Failed to retrieve repositories: {e}", ephemeral=True
        )


# Custom Select class for repository selection
class RepoSelect(discord.ui.Select):
    def __init__(self, options):
        super().__init__(placeholder="Choose a repository...", options=options)

    async def callback(self, interaction: discord.Interaction):
        repo_name = self.values[0]
        await display_repo_details(interaction, repo_name)


# View class to contain the select menu
class RepoSelectView(discord.ui.View):
    def __init__(self, options):
        super().__init__()
        self.add_item(RepoSelect(options))


# Function to display repository details
async def display_repo_details(interaction: discord.Interaction, repo_name: str):
    try:
        repo = await github_api_request(f"/repos/{github_org}/{repo_name}")
        embed = discord.Embed(
            title=repo["name"],
            url=repo["html_url"],
            description=repo["description"],
            color=discord.Color.blurple(),
        )
        embed.set_author(
            name=repo["owner"]["login"], icon_url=repo["owner"]["avatar_url"]
        )
        embed.add_field(name="Language", value=repo["language"], inline=True)
        embed.add_field(name="Stars", value=repo["stargazers_count"], inline=True)
        embed.add_field(name="Forks", value=repo["forks_count"], inline=True)

        await interaction.response.edit_message(embed=embed, view=None)

    except requests.exceptions.RequestException as e:
        await interaction.response.send_message(
            f"Failed to fetch repository: {e}", ephemeral=True
        )


# Slash command to search for repositories and present a select menu
@bot.tree.command(
    name="get_repo", description="Search and get details of a specific repository"
)
@app_commands.describe(keyword="Keyword to search for repositories")
async def get_repo(interaction: discord.Interaction, keyword: str):
    """Searches for repositories by keyword and allows selection."""
    try:
        search_results = await github_api_request(
            f"/search/repositories?q={keyword}+org:{github_org}"
        )
        repos = search_results.get("items", [])

        if not repos:
            await interaction.response.send_message(
                "No repositories found.", ephemeral=True
            )
            return

        # Limit to top 25 results due to Discord's select menu options limit
        options = [
            discord.SelectOption(
                label=repo["name"], description=(repo["description"] or "")[:100]
            )
            for repo in repos[:25]
        ]

        view = RepoSelectView(options)
        await interaction.response.send_message("Select a repository:", view=view)

    except requests.exceptions.RequestException as e:
        await interaction.response.send_message(
            f"Failed to search repositories: {e}", ephemeral=True
        )


@bot.tree.command(
    name="create_repo", description="Open a form to create a new repository"
)
async def create_repo(interaction: discord.Interaction):
    """Opens a modal form for creating a new repository."""
    await interaction.response.send_modal(CreateRepoModal())


@bot.tree.command(
    name="search_repos",
    description="Search for repositories in the GitHub organization",
)
async def search_repos(interaction: discord.Interaction):
    """Opens a modal to search for repositories."""
    await interaction.response.send_modal(SearchReposModal())


# ---------- Bot Events ----------
@bot.event
async def on_ready():
    # """Runs when the bot is ready."""
    # print(f"✅ Bot is ready and logged in as {bot.user}.")

    # cleared = bot.tree.clear_commands(guild=GUILD_ID)bun
    # print(f"🗑️ Cleared {cleared} commands for Guild ID {GUILD_ID.id}.")
    # # Sync commands globally and for the specified guild
    # # global_sync = await bot.tree.sync()
    # # print(f"🔄 Synced {len(global_sync)} global commands.")

    # bot.tree.copy_global_to(guild=GUILD_ID)
    # guild_sync = await bot.tree.sync(guild=GUILD_ID)
    # print(f"🏠 Synced {len(guild_sync)} commands for Guild ID {GUILD_ID.id}.")

    bot.tree.copy_global_to(guild=GUILD_ID)
    commands = await bot.tree.sync(guild=GUILD_ID)
    print(f"🔄 Synced {len(commands)} commands for Guild ID {GUILD_ID.id}.")


bot.run(DISCORD_TOKEN)
