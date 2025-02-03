import os
import random
import logging
from twitchio.ext import commands
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Bot(commands.Bot):
    def __init__(self):
        token = os.getenv('TWITCH_TOKEN')
        prefix = os.getenv('BOT_PREFIX', '!')  # Default prefix is '!'
        initial_channels = os.getenv('CHANNELS', '').split(',')  # Channels as comma-separated list

        if not token or not initial_channels:
            raise ValueError("Missing required environment variables. Check your .env file.")
        
        super().__init__(token=token, prefix=prefix, initial_channels=initial_channels)

    async def event_ready(self):
        logging.info(f'Logged in as | {self.nick}')

    @commands.command(name='r6pick')
    async def oprand(self, ctx: commands.Context):
        Aop = ["striker", "deimos", "ram", "brava", "grim", "sens", "osa", "flores", "zero", "ace", "iana", "kali", "amaru", "nøkk", "gridlock", "nomad", "maverick", "lion", "finka", "dokkaebi", "zofia", "ying", "jackal", "hibana", "capitão", "blackbeard", "buck", "sledge", "thatcher", "ash", "thermite", "montagne", "twitch", "blitz", "iq", "fuze", "glaz"]
        Dop = ["skopós", "sentry", "tubarão", "fenrir", "solis", "azami", "thorn", "thunderbird", "aruni", "melusi", "oryx", "wamai", "goyo", "warden", "mozzie", "kaid", "clash", "maestro", "alibi", "vigil", "ela", "lesion", "mira", "echo", "caveira", "valkyrie", "frost", "mute", "smoke", "castle", "pulse", "doc", "rook", "jager", "bandit", "tachanka", "kapkan"]

        
        Aop2 = random.choice(Aop)
        Dop2 = random.choice(Dop)
        
        await ctx.send(f"Attacker: {Aop2} \n Defender: {Dop2}")

if __name__ == "__main__":
    try:
        bot = Bot()
        bot.run()
    except Exception as e:
        logging.error(f"Bot encountered an error: {e}")
