import random
import twitchio
from twitchio.ext import commands

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            token='op',
            prefix='!',
            initial_channels=['queenrose4444']
        )

    async def event_ready(self):
        print(f'Logged in as | {self.nick}')  # Bot's nick from TwitchIO

    @commands.command(name='r6pick')
    async def oprand(self, ctx: commands.Context):
        Aop = [  "ram", "brava", "grim", "sens", "osa", "flores", "zero", "ace", "iana", "kali", "amaru", "nokk", "gridlock", "nomad", "maverick", "lion", "finka", "dokkaebi","zofia", "ying", "jackal", "hibana", "capito", "blackbeard", "buck", "sledge", "thatcher", "ash", "thermite", "montagne", "twitch", "blitz", "iq", "fuze", "glaz"  
        ]
        Dop = [   "tubarao", "fenrir", "solis", "azami", "thorn", "thunderbird", "aruni", "melusi", "oryx", "wamai", "goyo", "warden", "mozzie", "kaid", "clash", "maestro", "alibi","vigil", "ela", "lesion", "mira", "echo", "caveira", "valkrie", "frost", "mute", "smoke", "castle", "pulse", "doc", "rook", "jager", "bandit", "tachanka", "kapkan" 
        ]
        Aop2 = random.choice(Aop)
        Dop2 = random.choice(Dop)
        await ctx.send(f"Attacker: {Aop2} \n Defender: {Dop2}")
        
bot = Bot()
bot.run()
