import discord
from discord.ext import commands
import json

class Language_Modes(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print("Language_Modes.py is ready!")
        
    def update_modifier(self, guild_id, language):
        """Toggles 'australia_text' and ensures 'reversed_text' is disabled."""
        with open("cogs/jsonfiles/modify_text.json", "r") as j:
            text_modifiers = json.load(j)

        # Toggle 'australia_text' and disable 'reversed_text'
        text_modifiers[str(guild_id)]["language"] = language
        text_modifiers[str(guild_id)]["australia_text"] = False # Disable Australia mode
        text_modifiers[str(guild_id)]["reversed_text"] = False  # Disable Reverse mode
        text_modifiers[str(guild_id)]["balls_text"] = False  # Disable Balls mode

        # Save the updated file
        with open("cogs/jsonfiles/modify_text.json", "w") as j:
            json.dump(text_modifiers, j, indent=4)

        return text_modifiers[str(guild_id)]["language"]
        
    @commands.command(name="activate")
    async def change_language(self, ctx, *, language):
        language_codes = {
            'Afrikaans': 'af',
            'Albanian': 'sq',
            'Amharic': 'am',
            'Arabic': 'ar',
            'Armenian': 'hy',
            'Azerbaijani': 'az',
            'Basque': 'eu',
            'Belarusian': 'be',
            'Bengali': 'bn',
            'Bosnian': 'bs',
            'Bulgarian': 'bg',
            'Catalan': 'ca',
            'Cebuano': 'ceb',
            'Chinese (Simplified)': 'zh-CN',
            'Chinese (Traditional)': 'zh-TW',
            'Corsican': 'co',
            'Croatian': 'hr',
            'Czech': 'cs',
            'Danish': 'da',
            'Dutch': 'nl',
            'English': 'en',
            'Esperanto': 'eo',
            'Estonian': 'et',
            'Filipino': 'tl',
            'Finnish': 'fi',
            'French': 'fr',
            'Frisian': 'fy',
            'Galician': 'gl',
            'Georgian': 'ka',
            'German': 'de',
            'Greek': 'el',
            'Gujarati': 'gu',
            'Haitian Creole': 'ht',
            'Hausa': 'ha',
            'Hawaiian': 'haw',
            'Hebrew': 'he',
            'Hindi': 'hi',
            'Hmong': 'hmn',
            'Hungarian': 'hu',
            'Icelandic': 'is',
            'Igbo': 'ig',
            'Indonesian': 'id',
            'Irish': 'ga',
            'Italian': 'it',
            'Japanese': 'ja',
            'Javanese': 'jw',
            'Kannada': 'kn',
            'Kazakh': 'kk',
            'Khmer': 'km',
            'Kinyarwanda': 'rw',
            'Korean': 'ko',
            'Kurdish': 'ku',
            'Kyrgyz': 'ky',
            'Lao': 'lo',
            'Latin': 'la',
            'Latvian': 'lv',
            'Lithuanian': 'lt',
            'Luxembourgish': 'lb',
            'Macedonian': 'mk',
            'Malagasy': 'mg',
            'Malay': 'ms',
            'Malayalam': 'ml',
            'Maltese': 'mt',
            'Maori': 'mi',
            'Marathi': 'mr',
            'Mongolian': 'mn',
            'Myanmar (Burmese)': 'my',
            'Nepali': 'ne',
            'Norwegian': 'no',
            'Nyanja (Chichewa)': 'ny',
            'Odia (Oriya)': 'or',
            'Pashto': 'ps',
            'Persian': 'fa',
            'Polish': 'pl',
            'Portuguese': 'pt',
            'Punjabi': 'pa',
            'Romanian': 'ro',
            'Russian': 'ru',
            'Samoan': 'sm',
            'Scots Gaelic': 'gd',
            'Serbian': 'sr',
            'Sesotho': 'st',
            'Shona': 'sn',
            'Sindhi': 'sd',
            'Sinhala (Sinhalese)': 'si',
            'Slovak': 'sk',
            'Slovenian': 'sl',
            'Somali': 'so',
            'Spanish': 'es',
            'Mexican': 'es',
            'Sundanese': 'su',
            'Swahili': 'sw',
            'Swedish': 'sv',
            'Tajik': 'tg',
            'Tamil': 'ta',
            'Tatar': 'tt',
            'Telugu': 'te',
            'Thai': 'th',
            'Turkish': 'tr',
            'Turkmen': 'tk',
            'Ukrainian': 'uk',
            'Urdu': 'ur',
            'Uyghur': 'ug',
            'Uzbek': 'uz',
            'Vietnamese': 'vi',
            'Welsh': 'cy',
            'Xhosa': 'xh',
            'Yiddish': 'yi',
            'Yoruba': 'yo',
            'Zulu': 'zu'
        }

        
        lang_code = language_codes.get(language.capitalize())
        
        if not lang_code:
            await ctx.send("That is either not a language, or it is not one that I can speak.")
            return
        
        
        new_status = self.update_modifier(ctx.guild.id, lang_code)
        await ctx.send(f"Activating {language} mode.")

        
async def setup(client):
    await client.add_cog(Language_Modes(client))