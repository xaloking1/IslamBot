from aiohttp import ClientSession
from discord.ext import commands
from discord.ext.commands import MissingRequiredArgument
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_option

from utils.utils import get_site_source
import asyncio
import discord
import textwrap

INVALID_PERSON = "**Error**: Could not find person."
INVALID_ARGUMENTS = "**Error**: Please specify a name (in Arabic)."


class Biographies(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.session = ClientSession(loop=bot.loop)
        self.url = 'http://hadithtransmitters.hawramani.com/?s={}&cat=5563'

    async def _biography(self, ctx, name):
        soup = await get_site_source(self.url.format(name))

        try:
            permalink = soup.find('a', href=True, class_='sectionpermaanchor')['href']
        except TypeError:
            return await ctx.send("**Error**: Person not found.")

        soup = await get_site_source(permalink)

        text = soup.find('div', {"class": "definition"}).text
        title = soup.find('title').text

        pages = textwrap.wrap(text, 2040, break_long_words=False)

        num_pages = len(pages)

        em = discord.Embed(title='الذهبي - سير أعلام النبلاء', color=0x4aa807, description=pages[0])
        em.set_author(name=title)

        if num_pages > 1:
            page = 1
            em.set_footer(text=f'Page {page}/{num_pages}')

        msg = await ctx.send(embed=em)

        if num_pages > 1:
            await msg.add_reaction(emoji='⬅')
            await msg.add_reaction(emoji='➡')

        await msg.add_reaction(emoji='❎')

        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=180, check=lambda reaction, user:
                (reaction.emoji == '➡' or reaction.emoji == '⬅' or reaction.emoji == '❎')
                and user != self.bot.user
                and reaction.message.id == msg.id)

            except asyncio.TimeoutError:
                await msg.remove_reaction(emoji='➡', member=self.bot.user)
                await msg.remove_reaction(emoji='⬅', member=self.bot.user)
                await msg.remove_reaction(emoji='❎', member=self.bot.user)
                break

            if reaction.emoji == '➡':
                page -= 1
                if page < 1:
                    page = num_pages

            if reaction.emoji == '⬅':
                page += 1
                if page > num_pages:
                    page = 1

            if reaction.emoji == '❎':
                await msg.delete()

            em.description = pages[page - 1]
            em.set_footer(text=f'Page {page}/{num_pages}')
            await msg.edit(embed=em)

            try:
                await msg.remove_reaction(reaction.emoji, user)
            # The above fails if the bot doesn't have the "Manage Messages" permission, but it can be safely ignored
            # as it is not essential functionality.
            except discord.ext.commands.errors.CommandInvokeError:
                pass

    @commands.command(name="biography")
    async def biography(self, ctx, *, name):
        await self._biography(ctx, name)

    @biography.error
    async def biography_error(self, ctx, error):
        if isinstance(error, MissingRequiredArgument):
            await ctx.send("**Error**: Please type a valid name. For example: ")

    @cog_ext.cog_slash(name="biography", description="View the biography of a hadith transmitter or early Muslim.",
                       options=[
                           create_option(
                               name="name",
                               description="The *Arabic* name of the person to fetch information for, e.g. {}".format("عبد الله بن عباس "),
                               option_type=3,
                               required=True)])
    async def slash_biography(self, ctx: SlashContext, name: str):
        await ctx.respond()
        await self._biography(ctx, name)


def setup(bot):
    bot.add_cog(Biographies(bot))
