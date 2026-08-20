"""Tunable settings for the chef pipeline.

Everything you would reasonably want to change lives here, so the stage
modules stay free of magic numbers and hardcoded paths.
"""

from pathlib import Path

# Model used for every stage. Gemini via OpenRouter handles images, tool
# calling and structured output, which is all four stages between them.
# Swap to "gpt-5-nano" if you want to compare tool-calling behaviour.
MODEL = "openrouter:gemini-3.5-flash-lite"

# How many dishes to research. Each one costs a web-search agent run plus a
# coverage check, so this number drives most of the run cost.
MAX_RECIPES = 5

# How many fridge photos to send in one go. One shelf per photo works well.
# They travel in a single message so the model can tell that the same milk
# carton appearing in two shots is one carton, not two. Raising this costs
# input tokens on every stage-1 call, and vision models get less reliable
# the more images they have to hold at once.
MAX_IMAGES = 6

# config.py sits in chef/, so the lesson folder is one level up.
LESSON_DIR = Path(__file__).parent.parent
DEFAULT_IMAGE_DIR = LESSON_DIR / "resources" / "fridge"
REPORT_PATH = LESSON_DIR / "chef_report.md"

# Ingredients assumed to be in the kitchen already. Without this list every
# recipe scores badly, because nobody photographs their salt shaker. The
# coverage stage drops these from both the "have" and "missing" lists.
#
# Tuned for an Indian kitchen. Split by category so you can drop a whole
# group if it does not match how you actually cook.

_SEASONING = [
    "salt", "black salt", "kala namak", "sugar", "jaggery", "gur", "water",
]

_FATS = [
    "cooking oil", "vegetable oil", "sunflower oil", "olive oil",
    "mustard oil", "coconut oil", "ghee",
]

_GRAINS_AND_FLOURS = [
    "rice", "basmati rice", "atta", "whole wheat flour", "chapati", "roti",
    "maida", "all-purpose flour", "besan", "gram flour", "rava", "sooji",
    "semolina", "rice flour", "corn flour", "cornstarch", "poha",
    "flattened rice", "vermicelli", "sevai", "sabudana", "sago", "oats",
]

_LENTILS_AND_PULSES = [
    "toor dal", "arhar dal", "moong dal", "chana dal", "masoor dal",
    "urad dal", "rajma", "kidney beans", "chana", "chickpeas", "kabuli chana",
    "kala chana", "lobia", "black eyed peas",
]

_WHOLE_SPICES = [
    "cumin seeds", "jeera", "mustard seeds", "rai", "coriander seeds",
    "fennel seeds", "saunf", "fenugreek seeds", "methi seeds", "carom seeds",
    "ajwain", "nigella seeds", "kalonji", "asafoetida", "hing", "bay leaf",
    "tej patta", "cinnamon", "dalchini", "green cardamom", "elaichi",
    "black cardamom", "cloves", "laung", "black peppercorns",
    "dried red chillies", "star anise", "mace", "javitri", "nutmeg",
]

_GROUND_SPICES = [
    "turmeric", "haldi", "red chilli powder", "coriander powder",
    "dhania powder", "cumin powder", "garam masala", "chaat masala",
    "amchur", "dry mango powder", "kasuri methi", "sambar powder",
    "rasam powder", "pav bhaji masala", "kitchen king masala",
    "biryani masala", "black pepper", "pepper", "paprika", "oregano",
]

# The judgement call in this list. Indian kitchens genuinely always have
# these, but they are also substantial recipe ingredients rather than
# seasonings. Drop this group if you would rather see them scored.
_AROMATICS = [
    "onion", "garlic", "ginger", "green chilli", "curry leaves",
    "coriander leaves", "cilantro", "mint leaves",
]

_SOURING_AGENTS = [
    "tamarind", "imli", "lemon", "lime", "vinegar", "kokum",
]

_NUTS_AND_SEEDS = [
    "peanuts", "cashews", "almonds", "raisins", "sesame seeds", "til",
    "poppy seeds", "khus khus", "desiccated coconut", "dry coconut", "copra",
]

_CONDIMENTS = [
    "soy sauce", "tomato ketchup", "tomato puree", "pickle", "achar",
    "honey", "tea leaves", "coffee",
]

_LEAVENING = [
    "baking powder", "baking soda", "yeast", "eno", "fruit salt",
]

PANTRY_STAPLES = (
    _SEASONING
    + _FATS
    + _GRAINS_AND_FLOURS
    + _LENTILS_AND_PULSES
    + _WHOLE_SPICES
    + _GROUND_SPICES
    + _AROMATICS
    + _SOURING_AGENTS
    + _NUTS_AND_SEEDS
    + _CONDIMENTS
    + _LEAVENING
)

# Image formats we know how to label for the model. The mime type is required
# by the standard content block, it is not inferred from the bytes.
MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}
