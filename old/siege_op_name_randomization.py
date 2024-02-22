import random

Aop = [ #attackers
        "ram", "brava", "grim", "sens", "osa", "flores", "zero", "ace", "iana", "kali", "amaru", "nokk", "gridlock", "nomad", "maverick", "lion", "finka", "dokkaebi","zofia", "ying", "jackal", "hibana", "capito", "blackbeard", "buck", "sledge", "thatcher", "ash", "thermite", "montagne", "twitch", "blitz", "iq", "fuze", "glaz"
    ]
Dop = [ #defenders
    "tubarao", "fenrir", "solis", "azami", "thorn", "thunderbird", "aruni", "melusi", "oryx", "wamai", "goyo", "warden", "mozzie", "kaid", "clash", "maestro", "alibi","vigil", "ela", "lesion", "mira", "echo", "caveira", "valkrie", "frost", "mute", "smoke", "castle", "pulse", "doc", "rook", "jager", "bandit", "tachanka", "kapkan"
    ]

Aop2 = random.choice(Aop)
Dop2 = random.choice(Dop)

print("Atacker:", Aop2)
print("Defender:", Dop2)