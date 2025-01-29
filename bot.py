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

async def github_api_request(endpoint, method='GET', data=None):
    url = f'https://api.github.com{endpoint}'
    headers = {'Authorization': f'token {GITHUB_TOKEN}'}
    response = requests.request(method, url, headers=headers, json=data)
    response.raise_for_status()
    if response.headers.get('content-type') == 'application/json; charset=utf-8':
        return response.json()


@bot.command()
async def list_repos(ctx):
#   List all repos in the github org along with their urls
    repos = await github_api_request(f'/orgs/{github_org}/repos')
    for repo in repos:
        await ctx.send(f'{repo["name"]}: {repo["html_url"]}')

@bot.command()
async def get_repo(ctx, repo_name):
    repo = await github_api_request(f'/repos/{github_org}/{repo_name}')
    await ctx.send(repo['html_url'])

@bot.command()
async def search_repos(ctx, search_term):
    repos = await github_api_request(f'/search/repositories?q={search_term}+org:{github_org}')
    for repo in repos['items']:
        await ctx.send(f'{repo["name"]}: {repo["html_url"]}')
        
@bot.command()
async def create_repo(ctx, repo_name):
    data = {'name': repo_name, 'has_projects': True, 'team_id': 9478163}
    repo = await github_api_request(f'/orgs/{github_org}/repos', method='POST', data=data)
    team_repo_data = {
        'permission': 'maintain'
    }
    #/orgs/{org}/teams/{team_slug}/repos/{owner}/{repo}
    await github_api_request(f'/orgs/{github_org}/teams/campaigns/repos/{github_org}/{repo_name}', method='PUT', data=team_repo_data)
    await ctx.send(f'Repo created: {repo["html_url"]} with write access for the team.')
    
bot.run(DISCORD_TOKEN)
