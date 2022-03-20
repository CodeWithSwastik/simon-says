import os
import discord
from typing import Optional
from dotenv import load_dotenv

from utils import SimonSaysGame, StartView, ACCENT_COLOR

intents = discord.Intents.all()

bot = discord.Bot(
    intents=intents,
    allowed_mentions=discord.AllowedMentions(
        everyone=False, roles=True, users=True, replied_user=True
    ),
    activity=discord.Activity(
        type=discord.ActivityType.competing, name="a Simon says event!"
    ),
    debug_guilds=[681882711945641997],
)
bot.games = {}
bot.accent_color = ACCENT_COLOR

@bot.command()
async def start(ctx, role: discord.Role, channel: Optional[discord.TextChannel]):
    """
    Start a Simon Says Game!
    """
    channel = channel or ctx.channel

    if not ctx.author.guild_permissions.administrator and not discord.utils.find(
        lambda r: r.name == "Simon Says Controller", ctx.author.roles
    ):
        return await ctx.respond(
            "Only an admin or someone with the 'Simon Says Controller' role can start a game!",
            ephemeral=True,
        )

    if role.name != "Contestant":
        return await ctx.respond(
            "You may only use a role named Contestant for this.",
            ephemeral=True,
        )
    if ctx.guild.id in bot.games:
        c = bot.games[ctx.guild.id].channel.mention
        await ctx.respond(
            f"A simon says game is already running in {c}!", ephemeral=True
        )

    game = bot.games[ctx.guild.id] = SimonSaysGame(ctx.author, ctx.guild, role, channel)

    await ctx.respond(f"Starting a game in {channel.mention}!", ephemeral=True)

    em = discord.Embed(title="Simon says game!", description=f"Simon: {game.simon.mention}", color=bot.accent_color)
    em.set_thumbnail(url=bot.user.display_avatar.url)
    em.add_field(name="Player Count", value=str(game.player_count))
    await channel.send(embed=em, view=StartView(game=game))


@bot.event
async def on_message(msg):
    if msg.guild is None:
        return

    if msg.guild.id not in bot.games:
        return

    game = bot.games[msg.guild.id]
    if game.winner:
        del bot.games[msg.guild.id]

    if game.started and msg.channel == game.channel:
        await game.handle_message(msg, bot)


@bot.command()
@bot.user_command(name="Eliminate")
async def eliminate(ctx, member: discord.Member):
    """
    Eliminate a member!
    """

    if ctx.guild.id not in bot.games:
        return await ctx.respond(
            f"There is no active simon says game running in the server!", ephemeral=True
        )
    game = bot.games[ctx.guild.id]
    if ctx.author != game.simon:
        return await ctx.respond(
            f"You aren't the simon and cannot eliminate someone!", ephemeral=True
        )

    if member not in game.role.members:
        return await ctx.respond(f"That person isn't a competitor!", ephemeral=True)

    await game.eliminate(member, ctx)


@bot.command()
@bot.user_command(name="Revive")
async def revive(ctx, member: discord.Member):
    """
    Revive a member!
    """

    if ctx.guild.id not in bot.games:
        return await ctx.respond(
            f"There is no active simon says game running in the server!", ephemeral=True
        )
    game = bot.games[ctx.guild.id]
    if ctx.author != game.simon:
        return await ctx.respond(
            f"You aren't the simon and cannot revive someone!", ephemeral=True
        )

    if member in game.role.members:
        return await ctx.respond(
            f"That person is already a competitor!", ephemeral=True
        )

    await member.add_roles(game.role)
    await ctx.respond(f"{member.mention} has been revived!")


@bot.command()
async def remaining(ctx):
    """
    Check the remaining players!
    """

    if ctx.guild.id not in bot.games:
        return await ctx.respond(
            f"There is no active simon says game running in the server!", ephemeral=True
        )
    game = bot.games[ctx.guild.id]
    em = discord.Embed(
        title="Remaining Players",
        description=game.players_string,
        color=bot.accent_color,
    )
    em.set_footer(text=f"{game.player_count} left")
    await ctx.respond(embed=em)


@bot.command(name="new-simon")
async def new_simon(ctx, member: discord.Member):
    """
    Choose a new simon!
    """

    if ctx.guild.id not in bot.games:
        return await ctx.respond(
            f"There is no active simon says game running in the server!", ephemeral=True
        )
    game = bot.games[ctx.guild.id]
    if ctx.author != game.simon:
        return await ctx.respond(f"You aren't the simon!", ephemeral=True)

    game.simon = member
    await ctx.respond(f"{member.mention} is the new simon!")


load_dotenv()
bot.run(os.environ["TOKEN"])
