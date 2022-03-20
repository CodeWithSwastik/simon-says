import discord
import asyncio

ACCENT_COLOR = 0x5271FF


class SimonSaysGame:
    def __init__(
        self,
        simon: discord.Member,
        guild: discord.Guild,
        role: discord.Role,
        channel: discord.TextChannel,
    ):
        self.simon = simon
        self.guild = guild
        self.role = role
        self.channel = channel

        self.started = False
        self.winner = None

        self._elim_all = False
        self._simon_nick = "simon"
        self._talked = set()
        self._to_say = None
        self._to_not_say = None

    @property
    def player_count(self):
        return len(self.role.members)

    @property
    def players_string(self):
        return ', '.join(m.mention for m in self.role.members)

    @property
    def simon_says_line(self):
        return f"{self._simon_nick} says"

    async def start(self):
        self.started = True
        em = discord.Embed(
            title="Simon Says Game is Starting!",
            description=f"In this game you must listen to the Simon ({self.simon.mention}) and follow his orders. If you fail to do so you'll be eliminated! The last person remaining wins!",
            color=ACCENT_COLOR,
        )
        await self.channel.send(embed=em)
        await self.channel.send(
            f"Players ({self.player_count}): {self.players_string}"
        )

    async def eliminate(self, member: discord.Member, ctx=None, reason=None):
        await member.remove_roles(self.role)
        send = ctx.respond if ctx else self.channel.send
        await send(
            f"{member.mention} has been eliminated. {'Reason: '+reason if reason else 'How sad'}. {self.player_count} players remain."
        )
        await self.check_winner()

    async def mass_eliminate(self, members: list[discord.Member], reason=None):
        if self.winner:
            return
        embed = discord.Embed(title="Eliminating people...", description=f"Eliminating {len(members)} contenstant{'s' if len(members)>1 else ''}.", color=ACCENT_COLOR)
        if reason:
            embed.add_field(name="Reason", value=reason)
        ping = ", ".join(m.mention for m in members) or "** **"
        for m in members:
            await m.remove_roles(self.role)

        await self.channel.send(
            ping, embed=embed
        )
        await self.check_winner()

    async def handle_message(self, msg: discord.Message, bot: discord.Bot):
        msg.content = msg.content.lower()
        if msg.author == self.simon:
            if msg.content.startswith(self.simon_says_line):
                match msg.content.split()[2:]:
                    case [self._simon_nick, "is", "now", new_nick, *_]:
                        self._simon_nick = new_nick
                        await msg.add_reaction("✅")
                    case ["talk", *_] | ["afk", "check", *_]:
                        self._talked = set()
                        await asyncio.sleep(12)
                        await self.mass_eliminate([m for m in self.role.members if m not in self._talked], reason="AFK | Didn't talk")
                    case ["shut"] | ["don't", "talk"]:
                        self._elim_all = True
                        await asyncio.sleep(12)
                        self._elim_all = False
                    case ["change", "your", "status", "to", status, *_]:
                        await asyncio.sleep(12)
                        await self.mass_eliminate([m for m in self.role.members if str(m.status) != status.lower()], reason="Didn't change their status")

                    case ["change", "your", "nickname" | "name" | "nick", "to", *nick]:
                        nick = " ".join(nick)
                        await asyncio.sleep(16)
                        await self.mass_eliminate([m for m in self.role.members if str(m.display_name).lower() != nick], reason="Didn't change their name")

                    case ["say", *words]:
                        self._to_say = " ".join(words)
                        self._talked = set()
                        await asyncio.sleep(12)
                        await self.mass_eliminate([m for m in self.role.members if m not in self._talked], reason="AFK | Didn't talk")
                        self._to_say = None
                    case ["what", "is", *_] | ["what's", *_]:
                        self._talked = set()
                        await asyncio.sleep(16)
                        await self.mass_eliminate([m for m in self.role.members if m not in self._talked], reason="AFK | Didn't answer")

                if "below" in msg.content:
                    try:
                        m = await bot.wait_for(
                            "message",
                            check=lambda ms: ms.channel == self.channel,
                            timeout=15,
                        )
                    except asyncio.TimeoutError:
                        pass
                    if "lose" in msg.content:
                        await self.eliminate(m.author)
                    else:
                        await self.channel.send(
                            f"{m.author.mention} was the person below."
                        )

            else:
                words = msg.content.split()
                if len(words) > 1 and "say" in words[1]:
                    words = words[2:]

                match words:
                    case ["talk", *_] | ["afk", "check", *_]:
                        self._elim_all = True
                        await asyncio.sleep(12)
                        self._elim_all = False

                    case ["shut"] | ["don't", "talk"]:
                        self._talked = set()
                        await asyncio.sleep(12)
                        await self.mass_eliminate([m for m in self.role.members if m not in self._talked], reason="AFK | Didn't talk")

                    case ["change", "your", "status", "to", status, *_]:
                        await asyncio.sleep(12)
                        await self.mass_eliminate([m for m in self.role.members if str(m.status) == status.lower()], reason="Changed their status")
                    case ["change", "your", "nickname" | "name", "to", nick, *_]:
                        await asyncio.sleep(12)
                        await self.mass_eliminate([m for m in self.role.members if str(m.display_name).lower() == nick], reason="Changed their nickname")
                    case ["say", *words]:
                        self._to_not_say = " ".join(words)
                        await asyncio.sleep(12)
                        self._to_not_say = None

                if "below" in msg.content:
                    try:
                        m = await bot.wait_for(
                            "message",
                            check=lambda ms: ms.channel == self.channel,
                            timeout=15,
                        )
                    except asyncio.TimeoutError:
                        pass

                    if "win" in msg.content:
                        await self.eliminate(m.author)
                    else:
                        await self.channel.send(
                            f"{m.author.mention} was the person below."
                        )

        elif self.role in msg.author.roles:
            self._talked.add(msg.author)
            if self._elim_all:
                await self.eliminate(msg.author)
            if self._to_not_say and msg.content == self._to_not_say:
                await self.eliminate(msg.author)
            if self._to_say and msg.content != self._to_say:
                await self.eliminate(msg.author)

    async def check_winner(self):
        if self.winner:
            return
        if self.player_count == 1:
            self.winner = self.role.members[0]
            await self.channel.send(
                f"We have a winner! {self.winner.mention} has won the game! GG! Thanks for playing!"
            )
            await self.winner.remove_roles(self.role)
        elif self.player_count == 0:
            self.winner = True
            await self.channel.send(
                f"Everyone lost, no winner!"
            )           


class StartView(discord.ui.View):
    def __init__(self, game: SimonSaysGame):
        self.game = game
        super().__init__()

    @discord.ui.button(label="Join", style=discord.ButtonStyle.blurple, emoji="🙋‍♂️")
    async def join_callback(self, button, interaction: discord.Interaction):
        await interaction.user.add_roles(self.game.role)
        await interaction.response.send_message(
            "You are now a participant!", ephemeral=True
        )
        em = interaction.message.embeds[0]
        em.clear_fields()
        em.add_field(name="Player Count", value=str(self.game.player_count))
        em.add_field(name="Players", value=self.game.players_string)
        await interaction.message.edit(embed=em)

    @discord.ui.button(label="Start game!", style=discord.ButtonStyle.green, emoji="✨")
    async def start_callback(self, button, interaction: discord.Interaction):
        if interaction.user == self.game.simon:
            await interaction.response.send_message("Starting game!", ephemeral=True)
            self.stop()
            await self.game.start()

        else:
            await interaction.response.send_message(
                "You can't start the game, you aren't the simon!", ephemeral=True
            )
