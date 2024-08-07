# inputDict = {
#     "chunk_xHigh": 7,
#     "xLow": 46,
#     "chunk_xLow": 7,
#     "yLow": 153,
#     "xHigh": 46,
#     "numberOfPlanes": 1,
#     "plane": 0,
#     "chunk_yLow": 0,
#     "yHigh": 153,
#     "chunk_yHigh": 0
# }
# for k in inputDict.keys():
#     print(f"defDict[\"{k}\"] = wmd[\"{k}\"]")

inputStr = """
    -1 	debug 	(2656, 6912)
    0 	Gielinor Surface 	(3232, 3232)
    1 	Ancient Cavern 	(1760, 5344)
    2 	Ardougne Underground 	(2575, 9694)
    3 	Asgarnia Ice Cave 	(2989, 9566)
    4 	Braindeath Island 	(2144, 5101)
    5 	Dorgesh-Kaan 	(2720, 5344)
    6 	Dwarven Mines 	(3040, 9824)
    7 	God Wars Dungeon 	(2880, 5312)
    8 	Ghorrock Prison 	(2935, 6391)
    9 	Karamja Underground 	(2691, 9564)
    10 	Keldagrim 	(2879, 10176)
    11 	Miscellania Underground 	(2559, 10303)
    12 	Misthalin Underground 	(3168, 9632)
    13 	Mole Hole 	(1760, 5183)
    14 	Morytania Underground 	(3479, 9837)
    15 	Mos Le'Harmless Cave 	(3775, 9407)
    16 	Ourania Altar 	(3040, 5600)
    17 	Fremennik Slayer Cave 	(2784, 10016)
    18 	Stronghold of Security 	(1888, 5216)
    19 	Stronghold Underground 	(2432, 9812)
    20 	Taverley Underground 	(2912, 9824)
    21 	Tolna's Rift 	(3104, 5280)
    22 	Troll Stronghold 	(2822, 10087)
    23 	Mor Ul Rek 	(2489, 5118)
    24 	Lair of Tarn Razorlor 	(3168, 4564)
    25 	Waterbirth Dungeon 	(2495, 10144)
    26 	Wilderness Dungeons 	(3040, 10303)
    27 	Yanille Underground 	(2580, 9522)
    28 	Zanaris 	(2447, 4448)
    29 	Prifddinas 	(3263, 6079)
    30 	Fossil Island Underground 	(3744, 10272)
    31 	Feldip Hills Underground 	(1989, 9023)
    32 	Kourend Underground 	(1664, 10048)
    33 	Kebos Underground 	(1266, 10206)
    34 	Prifddinas Underground 	(3263, 12479)
    35 	Prifddinas Grand Library 	(2623, 6143)
    36 	LMS Desert Island 	(3456, 5824)
    37 	Tutorial Island 	(1695, 6111)
    38 	LMS Wild Varrock 	(3552, 6120)
    39 	Ruins of Camdozaal 	(2952, 5766)
    40 	The Abyss 	(3040, 4832)
    41 	Lassar Undercity 	(2656, 6368)
    42 	Kharidian Desert Underground 	(3488, 9504)
    43 	Varlamore Underground 	(1696, 9504)
    44 	Cam Torum 	(1440, 9568)
    45 	Neypotzli 	(1440, 9632)
    10000 	Abandoned Mine - Level 1 	(3424, 9632)
    10001 	Abandoned Mine - Level 2 	(2784, 4576)
    10002 	Abandoned Mine - Level 3 	(2720, 4512)
    10003 	Abandoned Mine - Level 4 	(2784, 4512)
    10004 	Abandoned Mine - Level 5 	(2720, 4448)
    10005 	Abandoned Mine - Level 6 	(2784, 4448)
    10006 	Abyss 	(3040, 4800)
    10007 	Abyssal Area 	(3040, 4896)
    10008 	Ah Za Rhoon 	(2912, 9344)
    10009 	Air altar 	(2848, 4832)
    10010 	Airship platform 	(2080, 5408)
    10011 	Ancient Cavern (unlit) 	(1632, 5312)
    10012 	Ancient Cavern lighting area 	(1568, 4896)
    10013 	Another Slice of H.A.M. Sigmund fight area 	(2528, 5568)
    10014 	Ape Atoll Dungeon 	(2752, 9120)
    10015 	Ardougne (Song of the Elves) 	(3360, 5920)
    10016 	Ardougne Sewer (Plague City) 	(2528, 9760)
    10017 	Baba Yaga's house 	(2464, 4640)
    10018 	Banana plantation (Ape Atoll) 	(2720, 9184)
    10019 	Barbarian Assault 	(1888, 5440)
    10020 	Barbarian Assault lobby 	(2592, 5280)
    10021 	Barrows crypts 	(3552, 9696)
    10022 	Blast Furnace 	(1952, 4960)
    10023 	Boots of lightness areas 	(2656, 9760)
    10024 	Bouncer's Cave 	(1760, 4704)
    10025 	Brimhaven Agility Arena 	(2784, 9568)
    10026 	Brine Rat Cavern 	(2720, 10144)
    10027 	Bryophyta's lair 	(3232, 9952)
    10028 	Burthorpe Games Room 	(2208, 4960)
    10029 	Cabin Fever boats 	(1824, 4832)
    10030 	Cerberus's Lair 	(1312, 1280)
    10031 	Corporeal Beast's lair 	(2976, 4256)
    10032 	Cosmic altar 	(2144, 4832)
    10033 	Cosmic entity's plane 	(2080, 4832)
    10034 	Courtroom 	(1824, 4256)
    10035 	Crandor Lab 	(2848, 9696)
    10036 	Crash Site Cavern 	(2112, 5664)
    10037 	Creature Creation 	(3040, 4384)
    10038 	Daeyalt Essence mine 	(3680, 9760)
    10039 	Death altar 	(2208, 4832)
    10040 	Desert Eagle Lair 	(3424, 9568)
    10041 	Desert Mining Camp dungeon 	(3296, 9440)
    10042 	Digsite Dungeon (rocks blown up) 	(3360, 9760)
    10043 	Digsite Dungeon (rocks intact) 	(3360, 9824)
    10044 	Dondakan's mine (during quest) 	(2368, 4960)
    10045 	Dorgesh-Kaan South Dungeon 	(2720, 5216)
    10046 	Dragon Slayer boats 	(2080, 5536)
    10047 	Dream World - challenges 	(1760, 5088)
    10048 	Dream World - Dream Mentor 	(1824, 5152)
    10049 	Dream World - Me 	(1824, 5088)
    10050 	Drill Demon 	(3168, 4832)
    10051 	Eadgar's cave 	(2912, 10080)
    10052 	Eagles' Peak Dungeon 	(2016, 4960)
    10053 	Elemental Workshop 	(2720, 9888)
    10054 	Enakhra's Temple 	(3104, 9312)
    10055 	Enchanted Valley 	(3040, 4512)
    10056 	Enlightened Journey crash areas 	(1824, 4896)
    10057 	Evil Bob's Island 	(2528, 4768)
    10058 	Evil Chicken's Lair 	(2464, 4384)
    10059 	Evil Twin 	(1888, 5152)
    10060 	Eyes of Glouphrie war cutscene 	(2144, 4960)
    10061 	Fairy Resistance Hideout 	(2336, 4448)
    10062 	Fisher Realm (diseased) 	(2784, 4704)
    10063 	Fisher Realm (healthy) 	(2656, 4704)
    10064 	Fishing Trawler 	(1952, 4832)
    10065 	Fishing Trawler 	(1888, 4832)
    10066 	Fishing Trawler 	(2016, 4832)
    10067 	Fossil Island boat 	(1824, 4768)
    10068 	Fragment of Seren fight 	(3296, 5920)
    10069 	Freaky Forester 	(2592, 4768)
    10070 	Genie cave 	(3360, 9312)
    10071 	Glarial's Tomb 	(2528, 9824)
    10072 	Goblin cook 	(2976, 9888)
    10073 	Gorak Plane 	(3040, 5344)
    10074 	H.A.M. Store room 	(2592, 5216)
    10075 	Hallowed Sepulchre - Level 1 	(2272, 5984)
    10076 	Hallowed Sepulchre starting area 	(2400, 5984)
    10077 	Harmony Island lower level 	(3808, 9248)
    10078 	Isafdar (Song of the Elves) 	(2784, 6112)
    10079 	Jaldraocht Pyramid - Level 1 	(2912, 4960)
    10080 	Jaldraocht Pyramid - Level 2 	(2848, 4960)
    10081 	Jaldraocht Pyramid - Level 3 	(2784, 4960)
    10082 	Jaldraocht Pyramid - Level 4 	(3232, 9312)
    10083 	Jatizso mine 	(2400, 10208)
    10084 	Jiggig Dungeon 	(2464, 9408)
    10085 	Jungle Eagle lair/Red chinchompa hunting ground 	(2528, 9312)
    10086 	Karamjan Temple 	(2848, 9280)
    10087 	Keep Le Faye (instance) 	(1696, 4256)
    10088 	Keldagrim Rat Pits 	(1952, 4704)
    10089 	Killerwatt Plane 	(2656, 5216)
    10090 	King's Ransom dungeon 	(1888, 4256)
    10091 	Kiss the frog 	(2464, 4768)
    10092 	Klenter's Pyramid 	(3296, 9184)
    10093 	Kruk's Dungeon 	(2496, 9152)
    10094 	Lady Trahaern hideout 	(2336, 9568)
    10095 	Library Historical Archive 	(1568, 10208)
    10096 	Lighthouse cutscene 	(2464, 4576)
    10097 	Lighthouse Dungeon 	(2528, 10016)
    10098 	Lighthouse Dungeon (cutscene) 	(2528, 4640)
    10099 	Lithkren Vault 	(1568, 5088)
    10100 	Lithkren Vault entrance (during quest) 	(3552, 10400)
    10101 	Lithkren Vault entrance (post-quest) 	(3552, 10464)
    10102 	Lizardman Temple 	(1312, 10080)
    10103 	Lumbridge Castle (Recipe for Disaster) 	(1888, 5344)
    10104 	Mage Training Arena rooms 	(3360, 9664)
    10105 	Maniacal monkey hunter area 	(2912, 9120)
    10106 	Meiyerditch Laboratories 	(3584, 9760)
    10107 	Meiyerditch Mine 	(2400, 4640)
    10108 	Mime 	(2016, 4768)
    10109 	Misthalin Mystery 	(1664, 4832)
    10110 	Mogre Camp 	(2976, 9504)
    10111 	Monkey Madness hangar (post-quest) 	(2656, 4512)
    10112 	Monkey Madness hangar and Bonzara 	(2400, 9888)
    10113 	Mourner Tunnels 	(1952, 4640)
    10114 	Mouse hole 	(2272, 5536)
    10115 	My Arm's Big Adventure boat cutscene 	(1888, 4896)
    10116 	Myreque Hideout (Burgh de Rott) 	(3488, 9632)
    10117 	Myreque Hideout (Canifis) 	(3456, 9856)
    10118 	Myreque Hideout (Meiyerditch) 	(3616, 9632)
    10119 	Nature altar 	(2400, 4832)
    10120 	Nightmare of Ashihama 	(3872, 9952)
    10121 	North-east Karamja cutscene 	(2528, 4576)
    10122 	Observatory Dungeon 	(2336, 9376)
    10123 	Ogre Enclave 	(2592, 9440)
    10124 	Old School Museum 	(3040, 9952)
    10125 	Paterdomus Temple underground 	(3424, 9888)
    10126 	Polar Eagle lair 	(2720, 10208)
    10127 	Prison Pete 	(2080, 4448)
    10128 	Puro-Puro 	(2592, 4320)
    10129 	Pyramid Plunder 	(1952, 4448)
    10130 	Quidamortem Cave 	(1184, 9952)
    10131 	Quiz Master 	(1952, 4768)
    10132 	Rantz's cave 	(2656, 9376)
    10133 	Rashiliyia's Tomb 	(2912, 9504)
    10134 	Ratcatchers Mansion 	(2848, 5088)
    10135 	Recipe for Disaster Ape Atoll Dungeon 	(3040, 5472)
    10136 	Recruitment Drive 	(2464, 4960)
    10137 	Rogues' Den 	(3008, 5024)
    10138 	Saba's cave 	(2272, 4768)
    10139 	Shadow Dungeon 	(2688, 5088)
    10140 	Skavid caves 	(2528, 9440)
    10141 	Smoke Dungeon 	(3264, 9376)
    10142 	Sophanem bank 	(2784, 5152)
    10143 	Sophanem Dungeon 	(3264, 9248)
    10144 	Sorceress's Garden 	(2912, 5472)
    10145 	Surprise Exam 	(1888, 5024)
    10146 	Tears of Guthix cave 	(3232, 9504)
    10147 	Temple of Ikov 	(2688, 9856)
    10148 	Temple of Marimbo Dungeon 	(2784, 9184)
    10149 	Temple Trekking 	(2080, 5024)
    10150 	Thammaron's throne room 	(2720, 4896)
    10151 	The Grand Tree - Monkey Madness II 	(1984, 5568)
    10152 	The Kendal's cave 	(2784, 10080)
    10153 	Train station 	(2464, 5536)
    10154 	Tree Gnome Village dungeon 	(2528, 9568)
    10155 	Tree Gnome Village dungeon (instance) 	(2592, 4448)
    10156 	Troll arena - Trollheim tunnel 	(2912, 10016)
    10157 	Trollweiss Dungeon 	(2784, 10208)
    10158 	Tunnel of Chaos 	(3168, 5216)
    10159 	Tutorial Island dungeon 	(3104, 9504)
    10160 	Tyras Camp cutscene 	(2336, 4576)
    10161 	Underground Pass - bottom level 	(2336, 9856)
    10162 	Underground Pass - bottom level (Song of the Elves instance) 	(2464, 6144)
    10163 	Underground Pass - first level 	(2432, 9696)
    10164 	Underground Pass - Iban's Temple (post-quest) 	(2016, 4704)
    10165 	Underground Pass - platforms 	(2144, 4640)
    10166 	Underground Pass - second level 	(2400, 9600)
    10167 	Underground Pass - swamp fail and final area 	(2464, 9632)
    10168 	Ungael Laboratory 	(2272, 10464)
    10169 	Uzer Dungeon 	(2720, 4896)
    10170 	Varrock Museum basement (higher) 	(1760, 4960)
    10171 	Varrock Museum basement (lower) 	(1632, 4960)
    10172 	Varrock Rat Pits 	(2912, 5088)
    10173 	Viyeldi caves (lower level) 	(2400, 4704)
    10174 	Viyeldi caves (upper level) 	(2784, 9312)
    10175 	Water Ravine Dungeon 	(3360, 9568)
    10176 	Waterfall Dungeon 	(2592, 9888)
    10177 	Waterfall Dungeon (water) 	(2528, 9888)
    10178 	Wilderness Wars 	(3296, 4640)
    10179 	Witchaven Dungeon 	(2336, 5088)
    10180 	Wrath altar 	(2336, 4832)
    10181 	Yanille cutscene 	(2912, 4704)
    10182 	Tutorial Island v2 dungeon 	(1696, 12512)
    10183 	Prifddinas Grand Library (post-quest) 	(3232, 12512)
    10184 	Temple Trekking 	(2848, 4576)
    10185 	Prifddinas rabbit cave 	(3296, 12576)
    10186 	Hallowed Sepulchre - Level 5 	(2272, 5856)
    10187 	Hallowed Sepulchre - Level 2 	(2528, 5984)
    10188 	Hallowed Sepulchre - Level 4 	(2528, 5856)
    10189 	Hallowed Sepulchre - Level 3 	(2400, 5824)
    10190 	Ardougne Prison 	(2592, 9696)
    10191 	Dragon Slayer II boat 	(1632, 5600) 
"""
lines = inputStr.split("\n")
for line in lines:
    if not line:
        continue
    line = line.split("\t")
    mapID, name, center = [item.strip() for item in line]
    print(f"\"{mapID}\": {name, eval(center)},")
# print(len(lines))
# print(lines[1])
# print(tuple(lines[1].split("\t")))