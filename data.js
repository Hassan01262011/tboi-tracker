
const CHARACTER_NAMES = {
  0:"Isaac",1:"Magdalene",2:"Cain",3:"Judas",4:"???",5:"Eve",6:"Samson",7:"Azazel",
  8:"Lazarus",9:"Eden",10:"The Lost",11:"Lazarus Risen",12:"Dark Judas",13:"Lilith",
  14:"Keeper",15:"Apollyon",16:"The Forgotten",17:"The Soul",18:"Bethany",19:"Jacob",
  20:"Esau",21:"Tainted Isaac",22:"Tainted Magdalene",23:"Tainted Cain",24:"Tainted Judas",
  25:"Tainted ???",26:"Tainted Eve",27:"Tainted Samson",28:"Tainted Azazel",
  29:"Tainted Lazarus",30:"Tainted Eden",31:"Tainted Lost",32:"Tainted Lilith",
  33:"Tainted Keeper",34:"Tainted Apollyon",35:"Tainted Forgotten",36:"Tainted Bethany",
  37:"Tainted Jacob",38:"Tainted Lazarus (Dead)",39:"Tainted Jacob (Lost)",40:"Extra/hidden PlayerType"
};

const MARK_LABELS = {
  MomsHeart:"Mom's Heart / It Lives",Isaac:"Isaac",Satan:"Satan",BossRush:"Boss Rush",
  BlueBaby:"???",Lamb:"The Lamb",MegaSatan:"Mega Satan",UltraGreed:"Greed / Greedier",
  Hush:"Hush",UltraGreedier:"Greedier (redundant field)",Delirium:"Delirium",Mother:"Mother",Beast:"The Beast"
};

const CHALLENGE_NAMES = [
"", "Pitch Black","High Brow","Head Trauma","Darkness Falls","The Tank","Solar System","Suicide King","Cat Got Your Tongue?",
"Demo Man","Cursed!","Glass Cannon","When Life Gives You Lemons","Beans!","It's in the Cards","Slow Roll","Computer Savvy",
"Waka Waka","The Host","The Family Man","Purist","XXXXXXXXL","SPEED!","Blue Bomber","PAY TO PLAY","Have a Heart","I RULE!",
"BRAINS!","Onan's Streak","The Guardian","Backasswards","Aprils Fool","Pokey Mans","Ultra Hard","Pong","Scat Man","Bloody Mary",
"Baptism by Fire","Isaac's Awakening","Seeing Double","Pica Run","Hot Potato","Cantripped!","Red Redemption","DELETE THIS"
];

// Names for especially useful/commonly searched collectibles. Every vanilla collectible ID 1-732 is still displayed.
const KNOWN_ITEMS = {
  1:"The Sad Onion",2:"The Inner Eye",3:"Spoon Bender",4:"Cricket's Head",5:"My Reflection",6:"Number One",7:"Blood of the Martyr",
  8:"Brother Bobby",9:"Skatole",10:"Halo of Flies",11:"1up!",12:"Magic Mushroom",13:"The Virus",14:"Roid Rage",15:"<3",
  33:"The Bible",34:"The Book of Belial",105:"The D6",118:"Brimstone",149:"Ipecac",169:"Polyphemus",224:"Cricket's Body",
  245:"20/20",331:"Godhead",395:"Tech X",416:"Deep Pockets",441:"Mega Blast",482:"Diplopia",489:"D Infinity",
  584:"Book of Virtues",585:"Alabaster Box",592:"Revelation",601:"Act of Contrition",647:"4.5 Volt",672:"A Pound of Flesh",
  673:"Redemption",689:"Glitched Crown",691:"Sacred Orb",696:"C Section",703:"Esau Jr.",706:"Abyss",710:"Bag of Crafting",
  711:"Flip",712:"Lemegeton",713:"Sumptorium",714:"Recall",715:"Hold",722:"Anima Sola",732:"Mom's Ring"
};

// Achievement names are filled for the major progression entries we know; every ID 1-638 is displayed regardless.
const KNOWN_ACHIEVEMENTS = {
  1:"Magdalene",2:"Cain",3:"Judas",4:"The Womb",5:"The Harbingers",6:"A Cube of Meat",7:"The Book of Revelations",
  8:"A Noose",9:"The Nail",10:"A Quarter",11:"A Fetus in a Jar",12:"A Small Rock",79:"Azazel",80:"Lazarus",81:"Eden",
  82:"The Lost",84:"The Real Platinum God",89:"Rune of Hagalaz",90:"Rune of Jera",91:"Rune of Ehwaz",92:"Rune of Dagaz",
  93:"Rune of Ansuz",94:"Rune of Perthro",95:"Rune of Berkano",96:"Rune of Algiz",235:"1001%",324:"Sin Collector",
  325:"Dedication",326:"ZIP!",327:"It's the Key",328:"Mr. Resetter!",336:"The Marathon",337:"RERUN",338:"Delirious",
  339:"1000000%",433:"Rock Bottom",447:"Redemption",463:"C Section",470:"Revelation",474:"Tainted Isaac",
  475:"Tainted Magdalene",476:"Tainted Cain",477:"Tainted Judas",478:"Tainted ???",479:"Tainted Eve",480:"Tainted Samson",
  481:"Tainted Azazel",482:"Tainted Lazarus",483:"Tainted Eden",484:"Tainted Lost",485:"Tainted Lilith",486:"Tainted Keeper",
  487:"Tainted Apollyon",488:"Tainted Forgotten",489:"Tainted Bethany",514:"Cantripped!",515:"Red Redemption",
  516:"DELETE THIS",517:"Dirty Mind",518:"Sigil of Baphomet",519:"Purgatory",520:"Spirit Sword",521:"Broken Glasses",
  584:"Spindown Dice",589:"Sumptorium",590:"Berserk!",591:"Hemoptysis",592:"Flip",594:"Ghost Bombs",595:"Gello",
  596:"Keeper's Kin",599:"Lemegeton"
};
