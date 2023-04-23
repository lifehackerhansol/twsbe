from asyncio import Queue

from discord.ext import commands


class SOAPDevice():
    def __init__(self, ctx, essential, serial):
        self.channel = ctx.channel
        self.essential = essential
        self.serial = serial


class SOAP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = Queue()

    async def processSOAP(self, queue):
        return

    @commands.command()
    async def soap(self, ctx, serial):
        if not ctx.message.attachments:
            await ctx.send("No attachments found! Please attach essential.exefs to the command.")
            return
        device = SOAPDevice(ctx, ctx.message.attachments[0].url)
        await self.queue.put(device)
        await ctx.send("Device added to queue!")


async def setup(bot):
    await bot.add_cog(SOAP(bot))
