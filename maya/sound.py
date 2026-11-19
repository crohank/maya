"""Non-speech sound identification on the CPU: CLAP zero-shot over LABELS names the sound;
AST (AudioSet, 527 classes) decides speech, timing and the crosswalk repeat-rate rule.

`identify(eng, wav)` returns (sentence, info). `wav` is float32 mono at 16 kHz.
Models are cached in `eng.cache` so only the first call pays the load.
"""
import re

import numpy as np

SR = 16000
AST_ID = "MIT/ast-finetuned-audioset-10-10-0.4593"
AST_WIN = int(10.24 * SR)  # AST input is fixed at 1024 frames; shorter audio is padded
CLAP_ID = "laion/clap-htsat-unfused"

# CLAP zero-shot list: everyday and street sounds, spoken as they appear in an answer.
# Written before the ESC-50 validation set existed; not edited after seeing its results.
LABELS = [
    "a siren", "an ambulance siren", "a police car siren", "a fire truck siren", "a car horn honking",
    "a truck air horn", "traffic noise", "a car passing by", "a car engine idling",
    "a car engine starting", "a motorcycle", "a bus", "a truck engine", "a train", "a train horn",
    "a subway train", "a tram bell", "a bicycle bell", "tires skidding", "a car alarm",
    "a truck reversing beeps", "a crosswalk signal beeping", "a crosswalk signal ticking",
    "a crosswalk voice saying walk sign is on", "a jackhammer", "a power drill", "hammering",
    "a chainsaw", "a lawn mower", "a leaf blower", "a helicopter", "an airplane flying overhead",
    "a jet engine", "footsteps", "people talking", "crowd chatter", "a man speaking",
    "a woman speaking", "a child speaking", "children playing", "laughing", "applause", "cheering",
    "shouting", "a whistle", "coughing", "sneezing", "breathing", "snoring", "a baby crying",
    "hands clapping", "a dog barking", "a dog growling", "a cat meowing", "a rooster crowing",
    "a hen clucking", "birds chirping", "a crow cawing", "pigeons cooing", "a cow mooing",
    "a pig oinking", "a sheep bleating", "a horse neighing", "a frog croaking", "crickets chirping",
    "insects buzzing", "a duck quacking", "an owl hooting", "rain", "thunder", "wind blowing",
    "ocean waves", "a stream of water flowing", "water dripping", "a crackling fire", "a clock ticking",
    "an alarm clock ringing", "a phone ringing", "a doorbell", "knocking on a door", "a door slamming",
    "a door creaking", "typing on a keyboard", "a mouse clicking", "a vacuum cleaner",
    "a washing machine", "a microwave beeping", "a kettle whistling", "water running from a tap",
    "a toilet flushing", "glass breaking", "dishes clattering", "food frying", "pouring water",
    "a can opening", "a zipper", "keys jangling", "chewing", "drinking", "brushing teeth",
    "a hair dryer", "an electric fan", "an air conditioner humming", "a smoke alarm beeping",
    "a fire alarm ringing", "church bells", "music playing", "someone singing", "a guitar", "a piano",
    "drums", "electronic beeping", "an elevator ding", "a cash register", "a camera shutter",
    "paper rustling", "a mosquito buzzing", "a bee buzzing", "silence", "static noise", "a gunshot",
    "fireworks", "a ticking timer",
]

# AudioSet name -> spoken phrase; see phrase() for names not listed.
PHRASE = {
    "Speech": "someone speaking", "Male speech, man speaking": "a man speaking",
    "Female speech, woman speaking": "a woman speaking", "Child speech, kid speaking": "a child speaking",
    "Conversation": "people talking", "Narration, monologue": "someone speaking",
    "Shout": "someone shouting", "Yell": "someone yelling", "Children shouting": "children shouting",
    "Screaming": "someone screaming", "Whispering": "someone whispering", "Laughter": "laughter",
    "Baby laughter": "a baby laughing", "Crying, sobbing": "someone crying",
    "Baby cry, infant cry": "a baby crying", "Singing": "someone singing", "Whistling": "someone whistling",
    "Breathing": "breathing", "Snoring": "snoring", "Cough": "coughing", "Sneeze": "sneezing",
    "Walk, footsteps": "footsteps", "Run": "someone running", "Chewing, mastication": "chewing",
    "Clapping": "clapping", "Cheering": "cheering", "Applause": "applause",
    "Chatter": "people chattering", "Crowd": "a crowd", "Hubbub, speech noise, speech babble": "a crowd talking",
    "Children playing": "children playing",
    "Dog": "a dog barking", "Bark": "a dog barking", "Yip": "a dog yipping", "Howl": "a dog howling",
    "Bow-wow": "a dog barking", "Growling": "growling", "Whimper (dog)": "a dog whimpering",
    "Cat": "a cat", "Purr": "a cat purring", "Meow": "a cat meowing", "Hiss": "hissing",
    "Horse": "a horse", "Clip-clop": "horse hooves", "Neigh, whinny": "a horse neighing",
    "Cattle, bovinae": "a cow", "Moo": "a cow mooing", "Pig": "a pig", "Oink": "a pig oinking",
    "Goat": "a goat", "Sheep": "a sheep", "Bleat": "a sheep or goat bleating",
    "Chicken, rooster": "a rooster or chicken", "Cluck": "a hen clucking",
    "Crowing, cock-a-doodle-doo": "a rooster crowing", "Duck": "a duck", "Quack": "a duck quacking",
    "Goose": "a goose", "Honk": "a goose honking", "Roaring cats (lions, tigers)": "a big cat roaring",
    "Bird": "birds", "Bird vocalization, bird call, bird song": "birds singing", "Chirp, tweet": "birds chirping",
    "Squawk": "a bird squawking", "Pigeon, dove": "pigeons", "Coo": "pigeons cooing", "Crow": "a crow",
    "Caw": "a crow cawing", "Owl": "an owl", "Hoot": "an owl hooting", "Bird flight, flapping wings": "wings flapping",
    "Insect": "insects", "Cricket": "crickets", "Mosquito": "a mosquito", "Fly, housefly": "a fly buzzing",
    "Buzz": "buzzing", "Bee, wasp, etc.": "a bee buzzing", "Frog": "a frog", "Croak": "a frog croaking",
    "Music": "music", "Guitar": "a guitar", "Piano": "a piano", "Drum": "a drum", "Drum kit": "drums",
    "Violin, fiddle": "a violin", "Flute": "a flute", "Bell": "a bell ringing", "Church bell": "church bells",
    "Bicycle bell": "a bicycle bell", "Chime": "a chime", "Wind chime": "wind chimes",
    "Wind": "wind", "Rustling leaves": "leaves rustling", "Wind noise (microphone)": "wind",
    "Thunderstorm": "a thunderstorm", "Thunder": "thunder", "Water": "water", "Rain": "rain",
    "Raindrop": "rain", "Rain on surface": "rain", "Stream": "a stream of water", "Waterfall": "a waterfall",
    "Ocean": "ocean waves", "Waves, surf": "ocean waves", "Fire": "a crackling fire", "Crackle": "crackling",
    "Boat, Water vehicle": "a boat", "Motorboat, speedboat": "a motorboat", "Ship": "a ship",
    "Vehicle": "a vehicle", "Motor vehicle (road)": "a motor vehicle", "Car": "a car",
    "Vehicle horn, car horn, honking": "a car horn honking", "Toot": "a horn tooting", "Car alarm": "a car alarm",
    "Skidding": "tires skidding", "Tire squeal": "tires squealing", "Car passing by": "a car passing by",
    "Race car, auto racing": "a race car", "Truck": "a truck", "Air brake": "a truck's air brakes",
    "Air horn, truck horn": "a truck horn", "Reversing beeps": "a vehicle reversing beeps",
    "Ice cream truck, ice cream van": "an ice cream truck", "Bus": "a bus",
    "Emergency vehicle": "an emergency vehicle siren", "Police car (siren)": "a police siren",
    "Ambulance (siren)": "an ambulance siren", "Fire engine, fire truck (siren)": "a fire truck siren",
    "Motorcycle": "a motorcycle", "Traffic noise, roadway noise": "traffic", "Rail transport": "a train",
    "Train": "a train", "Train whistle": "a train whistle", "Train horn": "a train horn",
    "Railroad car, train wagon": "a train", "Train wheels squealing": "train wheels squealing",
    "Subway, metro, underground": "a subway train", "Aircraft": "an aircraft", "Aircraft engine": "an aircraft engine",
    "Jet engine": "a jet engine", "Propeller, airscrew": "a propeller", "Helicopter": "a helicopter",
    "Fixed-wing aircraft, airplane": "an airplane", "Bicycle": "a bicycle", "Skateboard": "a skateboard",
    "Engine": "an engine", "Light engine (high frequency)": "a small engine", "Lawn mower": "a lawn mower",
    "Chainsaw": "a chainsaw", "Medium engine (mid frequency)": "an engine", "Heavy engine (low frequency)": "a heavy engine",
    "Engine starting": "an engine starting", "Idling": "an engine idling",
    "Accelerating, revving, vroom": "an engine revving", "Door": "a door", "Doorbell": "a doorbell",
    "Ding-dong": "a doorbell", "Sliding door": "a sliding door", "Slam": "a door slamming", "Knock": "knocking",
    "Tap": "tapping", "Squeak": "squeaking", "Dishes, pots, and pans": "dishes clattering",
    "Cutlery, silverware": "cutlery clinking", "Chopping (food)": "chopping", "Frying (food)": "food frying",
    "Microwave oven": "a microwave", "Blender": "a blender", "Water tap, faucet": "a running tap",
    "Sink (filling or washing)": "water running in a sink", "Hair dryer": "a hair dryer",
    "Toilet flush": "a toilet flushing", "Toothbrush": "teeth brushing", "Vacuum cleaner": "a vacuum cleaner",
    "Zipper (clothing)": "a zipper", "Keys jangling": "keys jangling", "Coin (dropping)": "coins dropping",
    "Typing": "typing", "Typewriter": "a typewriter", "Computer keyboard": "typing on a keyboard",
    "Alarm": "an alarm", "Telephone": "a telephone", "Telephone bell ringing": "a phone ringing",
    "Ringtone": "a phone ringtone", "Telephone dialing, DTMF": "phone dialing tones", "Alarm clock": "an alarm clock",
    "Siren": "a siren", "Civil defense siren": "a civil defense siren", "Buzzer": "a buzzer",
    "Smoke detector, smoke alarm": "a smoke alarm", "Fire alarm": "a fire alarm", "Foghorn": "a foghorn",
    "Whistle": "a whistle", "Clock": "a clock ticking", "Tick": "ticking", "Tick-tock": "a clock ticking",
    "Mechanical fan": "a fan", "Air conditioning": "an air conditioner", "Cash register": "a cash register",
    "Printer": "a printer", "Camera": "a camera shutter", "Hammer": "hammering", "Jackhammer": "a jackhammer",
    "Sawing": "sawing", "Power tool": "a power tool", "Drill": "a drill", "Explosion": "an explosion",
    "Gunshot, gunfire": "gunshots", "Fireworks": "fireworks", "Firecracker": "firecrackers",
    "Glass": "glass", "Chink, clink": "glass clinking", "Shatter": "glass shattering", "Splash, splatter": "splashing",
    "Drip": "water dripping", "Pour": "pouring liquid", "Boiling": "boiling water",
    "Smash, crash": "a crash", "Breaking": "something breaking", "Beep, bleep": "beeping",
    "Ping": "a ping", "Ding": "a ding", "Clicking": "clicking", "Sizzle": "sizzling", "Hum": "a humming sound",
    "Silence": "silence", "Rustle": "rustling", "Chirp tone": "electronic chirping", "Pulse": "pulsing beeps",
    "Television": "a television", "Radio": "a radio", "White noise": "static noise", "Static": "static noise",
    # Sound-quality classes, named after the sound rather than its source.
    "Burst, pop": "a popping sound", "Boom": "a boom", "Chop": "chopping", "Splinter": "wood splintering",
    "Crack": "a cracking sound", "Slosh": "water sloshing", "Squish": "a squishing sound",
    "Trickle, dribble": "trickling water", "Gush": "gushing water", "Fill (with liquid)": "liquid filling a container",
    "Spray": "spraying", "Pump (liquid)": "a pump", "Stir": "stirring", "Thump, thud": "a thud", "Thunk": "a thunk",
    "Bang": "a bang", "Slap, smack": "a slap", "Whack, thwack": "a whack", "Bouncing": "something bouncing",
    "Whip": "a whip crack", "Flap": "flapping", "Scratch": "scratching", "Scrape": "scraping", "Rub": "rubbing",
    "Roll": "something rolling", "Crushing": "crushing", "Crumpling, crinkling": "crinkling", "Tearing": "tearing",
    "Clang": "a metal clang", "Squeal": "a squeal", "Creak": "creaking", "Whir": "a whirring sound",
    "Clatter": "clattering", "Clickety-clack": "a clickety-clack", "Rumble": "rumbling", "Plop": "a plop of water",
    "Jingle, tinkle": "jingling", "Zing": "a zing", "Boing": "a boing", "Crunch": "crunching",
    "Rattle": "rattling", "Rattle (instrument)": "a rattle", "Snort": "snorting", "Grunt": "grunting",
    "Gasp": "a gasp", "Pant": "panting", "Wheeze": "wheezing", "Sniff": "sniffing", "Throat clearing": "throat clearing",
    "Sigh": "a sigh", "Groan": "groaning", "Whimper": "whimpering", "Wail, moan": "wailing", "Gargling": "gargling",
    "Stomach rumble": "a stomach rumbling", "Burping, eructation": "burping", "Hiccup": "hiccups", "Fart": "a fart",
    "Finger snapping": "fingers snapping", "Heart sounds, heartbeat": "a heartbeat",
    "Change ringing (campanology)": "bells ringing", "Single-lens reflex camera": "a camera shutter",
    "Gears": "gears turning", "Ratchet, pawl": "a ratchet", "Sewing machine": "a sewing machine",
    "Scissors": "scissors", "Electric shaver, electric razor": "an electric shaver", "Shuffling cards": "cards shuffling",
    "Writing": "writing", "Cupboard open or close": "a cupboard door", "Drawer open or close": "a drawer",
    "Electric toothbrush": "an electric toothbrush", "Mouse": "a mouse squeaking", "Patter": "pattering",
    "Rodents, rats, mice": "rodents", "Turkey": "a turkey", "Gobble": "a turkey gobbling",
    "Whale vocalization": "a whale", "Snake": "a snake", "Steam": "hissing steam", "Gurgling": "gurgling water",
    "Dental drill, dentist's drill": "a dental drill", "Filing (rasp)": "filing", "Sanding": "sanding",
    "Bathtub (filling or washing)": "a bathtub filling", "Wind noise (microphone)": "wind",
    "Keyboard (musical)": "a keyboard instrument", "Jingle (music)": "a jingle",
    "Inside, small room": "a small room", "Outside, urban or manmade": "a city street",
    "Inside, large room or hall": "a large hall", "Inside, public space": "a public space",
    "Outside, rural or natural": "the outdoors", "Canidae, dogs, wolves": "a dog or wolf", "Chuckle, chortle": "chuckling",
    "Domestic animals, pets": "a pet animal", "Livestock, farm animals, working animals": "farm animals",
}


def phrase(name):
    """Spoken phrase for an AudioSet class: the map above, else the name without its parenthetical."""
    if name in PHRASE:
        return PHRASE[name]
    return re.sub(r"\s*\(.*?\)", "", name).split(",")[0].strip().lower()

# Parent or scene classes: spoken only when nothing more specific scores.
GENERIC = {
    "Animal", "Domestic animals, pets", "Livestock, farm animals, working animals", "Wild animals", "Fowl",
    "Canidae, dogs, wolves", "Musical instrument", "Plucked string instrument", "Percussion",
    "Vehicle", "Motor vehicle (road)", "Rail transport", "Aircraft", "Mechanisms", "Tools", "Liquid",
    "Inside, small room", "Inside, large room or hall", "Inside, public space", "Outside, urban or manmade",
    "Outside, rural or natural", "Reverberation", "Echo", "Noise", "Environmental noise", "Sound effect",
    "Field recording", "Wood", "Glass", "Door", "Hands", "Water", "Engine", "Speech synthesizer",
    "Bird", "Insect", "Music", "Sine wave", "Harmonic", "Vibration", "Throbbing", "Distortion", "Sidetone",
    "Cacophony", "Mains hum", "Pink noise", "White noise", "Static", "Silence", "Hum", "Whoosh, swoosh, swish",
}


def pulse_rate(wav):
    """Dominant repeat rate of short onsets: (rate_hz, regularity 0..1, sustained_s).

    Crosswalk signals repeat at a fixed rate: a locator tone about once per
    second, a walk indication as rapid ticks at about 8 to 10 per second (US
    MUTCD 4E). AudioSet has no crosswalk class, so this rate is the only cue
    that separates them from other beeps.
    """
    hop, n = 160, 512
    if len(wav) < SR:
        return 0.0, 0.0, 0.0
    frames = np.lib.stride_tricks.sliding_window_view(wav, n)[::hop] * np.hanning(n)
    mag = np.abs(np.fft.rfft(frames, axis=1))[:, 16:]  # above 500 Hz: ticks and beeps, not engine rumble
    flux = np.maximum(np.diff(np.log1p(mag * 10), axis=0), 0).sum(1)
    flux = flux - np.convolve(flux, np.ones(50) / 50, mode="same")
    flux = np.maximum(flux, 0)
    if flux.std() == 0:
        return 0.0, 0.0, 0.0
    ac = np.correlate(flux, flux, mode="full")[len(flux) - 1:]
    ac = ac / (ac[0] + 1e-9)
    fps = SR / hop
    lo, hi = int(fps / 15), int(fps / 0.6)   # 0.6 to 15 repeats per second
    lags = np.arange(lo, min(hi, len(ac)))
    # Peak height over the half-lag value: noise has a smooth, high ac at short lags.
    prom = ac[lags] - ac[lags // 2]
    # Multiples of the true period score about as high; take the shortest lag near the best.
    best = int(np.flatnonzero(prom >= 0.8 * prom.max())[0])
    lag, reg = int(lags[best]), float(prom[best])
    peaks = flux > (flux.mean() + 2 * flux.std())
    span = (np.flatnonzero(peaks)[-1] - np.flatnonzero(peaks)[0]) / fps if peaks.any() else 0.0
    return round(fps / lag, 2), round(reg, 3), round(float(span), 2)


def _windows(wav, win):
    """Start offsets of non-overlapping windows; the last one is aligned to the end."""
    if len(wav) <= win:
        return [0]
    starts = list(range(0, len(wav) - win, win))
    return starts + [len(wav) - win]


def ast_model(eng):
    if "ast" not in eng.cache:
        from transformers import AutoFeatureExtractor, AutoModelForAudioClassification
        fx = AutoFeatureExtractor.from_pretrained(AST_ID)
        model = AutoModelForAudioClassification.from_pretrained(AST_ID).eval()
        eng.cache["ast"] = (fx, model, [model.config.id2label[i] for i in range(model.config.num_labels)])
    return eng.cache["ast"]


def ast_probs(eng, wav):
    """Sigmoid scores per window, shape (windows, 527), and window start seconds.

    AudioSet is multi-label, so sigmoid, not the softmax the HF pipeline applies.
    """
    import torch
    fx, model, _ = ast_model(eng)
    starts = _windows(wav, AST_WIN)
    x = fx([wav[s:s + AST_WIN] for s in starts], sampling_rate=SR, return_tensors="pt")
    with torch.inference_mode():
        p = torch.sigmoid(model(**x).logits).numpy()
    return p, [s / SR for s in starts]


def clap_model(eng):
    if "clap" not in eng.cache:
        import torch
        from transformers import ClapModel, ClapProcessor
        proc = ClapProcessor.from_pretrained(CLAP_ID)
        model = ClapModel.from_pretrained(CLAP_ID).eval()
        with torch.inference_mode():
            tok = proc.tokenizer([f"This is a sound of {l}." for l in LABELS], padding=True, return_tensors="pt")
            te = torch.nn.functional.normalize(_emb(model.get_text_features(**tok)), dim=-1)
            scale = float(model.logit_scale_a.exp())
        eng.cache["clap"] = (proc, model, te, scale)
    return eng.cache["clap"]


def _emb(out):
    # transformers 5 returns an output object from get_*_features; older versions a tensor.
    return out if hasattr(out, "dim") else out.pooler_output


def clap_ranked(eng, wav):
    """LABELS as (phrase, prob, phrase), best first. 10 s windows at 48 kHz, embeddings averaged."""
    import torch
    from scipy.signal import resample_poly
    proc, model, te, scale = clap_model(eng)
    win = 10 * SR
    chunks = [resample_poly(wav[s:s + win], 3, 1).astype(np.float32) for s in _windows(wav, win)]
    f = proc.feature_extractor(chunks, sampling_rate=48000, return_tensors="pt")
    with torch.inference_mode():
        ae = torch.nn.functional.normalize(_emb(model.get_audio_features(**f)), dim=-1).mean(0)
        p = torch.softmax(scale * (te @ ae), dim=0).numpy()
    return [(LABELS[j], round(float(p[j]), 3), LABELS[j]) for j in np.argsort(-p)[:10]]


SPEECHY = {"Speech", "Male speech, man speaking", "Female speech, woman speaking", "Child speech, kid speaking",
           "Conversation", "Narration, monologue", "Babbling", "Speech synthesizer"}


def ranked(agg, names, skip=()):
    """AST classes as (phrase, score, name), best first; parent classes count half."""
    out, seen = [], set()
    for j in np.argsort(-agg)[:25]:
        name = names[j]
        if name in skip:
            continue
        ph = phrase(name)
        sc = float(agg[j]) * (0.5 if name in GENERIC else 1.0)
        out.append((ph, sc, name))
    out.sort(key=lambda x: -x[1])
    res = []
    for ph, sc, name in out:
        if ph not in seen:
            seen.add(ph)
            res.append((ph, round(sc, 3), name))
    return res


def background(eng, agg, min_score=0.2):
    """The strongest non-speech sound under speech, or None."""
    names = ast_model(eng)[2]
    r = [x for x in ranked(agg, names, SPEECHY | GENERIC) if x[1] >= min_score]
    return r[0][0] if r else None


# AST classes a crosswalk locator tone tends to land on (synthetic 880 Hz beeps scored DTMF first).
BEEPY = {"Beep, bleep", "Ping", "Sine wave", "Chirp tone", "Buzzer", "Telephone dialing, DTMF", "Dial tone",
         "Busy signal", "Electronic tuner", "Reversing beeps", "Pulse", "Chirp, tweet", "Tick", "Clicking"}
CLOCKY = {"Tick-tock", "Clock"}

# Tonal sweeps also give a steady onset rate (a yelp siren measured 7 per second), so these veto the tick rule.
SIRENY = {"Siren", "Civil defense siren", "Emergency vehicle", "Police car (siren)", "Ambulance (siren)",
          "Fire engine, fire truck (siren)", "Car alarm", "Alarm", "Smoke detector, smoke alarm", "Fire alarm",
          "Music", "Singing", "Musical instrument", "Bird vocalization, bird call, bird song"}
STOP = {"a", "an", "the", "or", "of", "someone", "sound", "noise", "like", "and", "maybe"}


def _words(text):
    return set(re.findall(r"[a-z]+", text)) - STOP


def name_sound(r):
    """Sentence for a ranked list; the second guess must be a different sound, not a synonym or parent."""
    top = r[0]
    alt = next((x for x in r[1:] if x[2] not in GENERIC and not _words(x[0]) & _words(top[0])), None)
    alt_ok = alt is not None and alt[1] >= 0.25 * top[1]
    if top[1] < 0.15:
        return f"I am not sure. It might be {top[0]}" + (f", or {alt[0]}." if alt_ok else ".")
    if top[1] >= 0.4 and (not alt_ok or alt[1] < 0.6 * top[1]):
        return f"It sounds like {top[0]}."
    return f"It sounds like {top[0]}" + (f", or possibly {alt[0]}." if alt_ok else ".")


def timeline(probs, starts, names, dur):
    """[(phrase, start_s, end_s)] of the top sound per AST window, neighbours merged."""
    segs = []
    for p, s in zip(probs, starts):
        r = ranked(p, names, SPEECHY)
        ph = r[0][0] if r[0][1] >= 0.15 else None
        end = min(dur, s + AST_WIN / SR)
        if segs and (segs[-1][0] == ph or (ph and segs[-1][0] and _words(ph) & _words(segs[-1][0]))):
            segs[-1][2] = end
        else:
            segs.append([ph, s, end])
    return [tuple(x) for x in segs if x[0]]


def identify(eng, wav, probs=None, starts=None):
    """One or two short sentences naming the sound, with a second guess when unsure."""
    if probs is None:
        probs, starts = ast_probs(eng, wav)
    agg = probs.max(0)
    names = ast_model(eng)[2]
    r = ranked(agg, names, SPEECHY)
    # Pack sound items: AST 9/10, CLAP 10/10; ESC-50 validation: AST 74/100, CLAP 84/100.
    rc = clap_ranked(eng, wav) if eng.opts.get("sound", "clap") == "clap" else None
    out = name_sound(rc or r)
    segs = timeline(probs, starts, names, len(wav) / SR) if len(probs) > 1 else []
    if len({s[0] for s in segs}) > 1:
        out = "I hear several sounds: " + ", then ".join(
            f"{p} from {a:.0f} to {b:.0f} seconds" for p, a, b in segs[:5]) + "."
    rate, reg, span = pulse_rate(wav)
    top_names = {n for _, sc, n in r[:5] if sc >= 0.2}
    if reg >= 0.4 and 6 <= rate <= 14 and span >= 2 and not top_names & SIRENY:
        out = (f"I hear a rapid, steady ticking, about {rate:.0f} per second, like a crosswalk walk signal. "
               + out.replace("It sounds", "It also sounds"))
    elif reg >= 0.4 and 0.7 <= rate <= 1.5 and {n for _, _, n in r[:5]} & BEEPY and not top_names & CLOCKY:
        out += " It repeats about once a second, which could be a crosswalk button tone."
    detected = ", ".join(f"{p} {s:.2f}" for p, s, _ in (rc or r)[:5])
    return out, {"detected": detected, "ast_top": ", ".join(f"{p} {s:.2f}" for p, s, _ in r[:5]),
                 "pulse": [rate, reg, span]}
