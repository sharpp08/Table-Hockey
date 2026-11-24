"""Thirty campaign rewards for the player's air-hockey paddle."""
SKINS = [
    ("DEFAULT BLUE", (56, 140, 255), (190, 230, 255), "core"),
    ("CRIMSON FLARE", (235, 55, 75), (255, 190, 120), "flare"),
    ("TOXIC LIME", (130, 230, 65), (225, 255, 150), "orbit"),
    ("VIOLET PULSE", (155, 85, 255), (225, 185, 255), "core"),
    ("GOLD RUSH", (255, 180, 45), (255, 240, 160), "orbit"),
    ("ARCTIC FROST", (65, 220, 245), (220, 255, 255), "core"),
    ("HOT PINK", (255, 65, 175), (255, 205, 235), "flare"),
    ("EMERALD EDGE", (35, 190, 125), (170, 255, 210), "orbit"),
    ("PHANTOM", (115, 130, 160), (235, 245, 255), "core"),
    ("SOLAR GOLD", (255, 125, 35), (255, 235, 125), "flare"),
    ("CYBER TEAL", (25, 210, 205), (175, 255, 250), "orbit"),
    ("ROYAL PURPLE", (115, 65, 220), (205, 175, 255), "core"),
    ("LASER RED", (255, 35, 45), (255, 190, 190), "flare"),
    ("NEON MINT", (90, 255, 175), (220, 255, 230), "orbit"),
    ("DEEP SPACE", (65, 85, 180), (175, 205, 255), "core"),
    ("MAGMA", (245, 85, 25), (255, 210, 80), "flare"),
    ("SAPPHIRE", (35, 105, 235), (175, 220, 255), "orbit"),
    ("CANDY POP", (245, 95, 210), (255, 220, 245), "core"),
    ("RADIOACTIVE", (185, 245, 25), (245, 255, 170), "flare"),
    ("STORM", (95, 115, 145), (210, 230, 255), "orbit"),
    ("AURORA", (45, 205, 170), (190, 255, 225), "core"),
    ("INFERNO", (255, 65, 25), (255, 220, 125), "flare"),
    ("GALAXY", (105, 65, 205), (235, 190, 255), "orbit"),
    ("ICE NOVA", (90, 190, 255), (240, 255, 255), "core"),
    ("JADE DRAGON", (25, 155, 95), (190, 255, 175), "flare"),
    ("ULTRAVIOLET", (175, 55, 245), (245, 195, 255), "orbit"),
    ("CHAMPION", (255, 205, 55), (255, 255, 220), "core"),
    ("QUANTUM", (45, 225, 235), (245, 255, 255), "flare"),
    ("OMEGA", (235, 235, 245), (255, 205, 80), "orbit"),
    ("LEGENDARY", (255, 215, 70), (255, 255, 245), "legend"),
]

def get_skin(level):
    index = max(1, min(len(SKINS), int(level))) - 1
    name, color, accent, pattern = SKINS[index]
    return {"id": index + 1, "name": name, "color": color, "accent": accent, "pattern": pattern}

def get_skin_name(level):
    return get_skin(level)["name"]
