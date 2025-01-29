import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import os

load_dotenv()

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

intents=discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)
github_org = 'tagglabs'
import requests

def github_api_request(endpoint, method='GET', data=None):
    url = f'https://api.github.com{endpoint}'
    headers = {'Authorization': f'token {GITHUB_TOKEN}'}
    response = requests.request(method, url, headers=headers, json=data)
    return response.json()

@bot.command()
async def list_repos(ctx):
#   List all repos in the github org along with their urls
    repos = github_api_request(f'/orgs/{github_org}/repos')
    for repo in repos:
        await ctx.send(f'{repo["name"]}: {repo["html_url"]}')

@bot.command()
async def get_repo(ctx, repo_name):
    repo = github_api_request(f'/repos/{github_org}/{repo_name}')
    await ctx.send(repo['html_url'])

@bot.command()
async def search_repos(ctx, search_term):
    repos = github_api_request(f'/search/repositories?q={search_term}+org:{github_org}')
    for repo in repos['items']:
        await ctx.send(f'{repo["name"]}: {repo["html_url"]}')
        
@bot.command()
async def create_repo(ctx, repo_name):
    data = {'name': repo_name}
    repo = github_api_request(f'/orgs/{github_org}/repos', method='POST', data=data)
    await ctx.send(repo['html_url'])

bot.run(DISCORD_TOKEN)
