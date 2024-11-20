import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ContextTypes
)
from deep_translator import GoogleTranslator
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import urllib.request
import requests
from flask import Flask
from threading import Thread

# Flask setup to keep bot alive
app = Flask('')

@app.route('/')
def home():
    return "Hello. I am alive!"

def run():
    app.run(host='0.0.0.0', port=80)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Telegram Bot
class WordTranslatorBot:
    def __init__(self, token):
        self.token = token
        self.translator = GoogleTranslator(source='en', target='uk')
        self.words = []
        self.setup_font()

    def setup_font(self):
        font_path = "DejaVuSans.ttf"
        if not os.path.exists(font_path):
            font_url = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf"
            urllib.request.urlretrieve(font_url, font_path)
        pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))

    def get_pronunciation(self, word):
        try:
            url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0 and 'phonetic' in data[0]:
                    return data[0]['phonetic']
                elif data and len(data) > 0 and 'phonetics' in data[0] and len(data[0]['phonetics']) > 0:
                    phonetics = data[0]['phonetics']
                    for phonetic in phonetics:
                        if 'text' in phonetic and phonetic['text']:
                            return phonetic['text']
            return ""
        except:
            return ""

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [["📄 Передати слова"]]
        reply_markup = ReplyKeyboardMarkup(
            keyboard, resize_keyboard=True, one_time_keyboard=False
        )
        await update.message.reply_text(
            "Вітаю! Надсилайте слова англійською мовою. "
            "Я їх збиратиму, а потім створю PDF з перекладом та транскрипцією.",
            reply_markup=reply_markup
        )

    async def collect_words(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.strip()
        if text == "📄 Передати слова":
            await self.create_translation_pdf(update)
        elif text:
            self.words.append(text)
            pronunciation = self.get_pronunciation(text)
            response_text = f"Додано слово: {text}"
            if pronunciation:
                response_text += f"\nТранскрипція: {pronunciation}"
            await update.message.reply_text(response_text)

    async def create_translation_pdf(self, update: Update):
        if not self.words:
            await update.message.reply_text("Немає слів для передавання.")
            return

        try:
            translations = []
            for word in self.words:
                translation = self.translator.translate(word)
                pronunciation = self.get_pronunciation(word)
                translations.append((word, pronunciation, translation))

            pdf_path = "vocabulary.pdf"
            c = canvas.Canvas(pdf_path, pagesize=letter)
            width, height = letter

            c.setFont("DejaVuSans", 12)
            y = height - 100

            # Заголовок
            c.drawString(100, height - 50, "English - Pronunciation - Ukrainian")

            # Додавання слів
            for eng, pron, ukr in translations:
                text = f"{eng}"
                if pron:
                    text += f" [{pron}]"
                text += f" : {ukr}"

                c.drawString(100, y, text)
                y -= 20
                if y <= 50:
                    c.showPage()
                    c.setFont("DejaVuSans", 12)
                    y = height - 100

            c.save()

            with open(pdf_path, 'rb') as pdf_file:
                await update.message.reply_document(
                    pdf_file, 
                    caption="Ось ваш PDF зі словами, транскрипцією та перекладами!"
                )

            self.words.clear()
            os.remove(pdf_path)
        except Exception as e:
            await update.message.reply_text(f"Виникла помилка при створенні PDF: {str(e)}")

    def run(self):
        app = Application.builder().token(self.token).build()

        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.collect_words))

        print("Бот запущено...")
        app.run_polling()

if __name__ == "__main__":
    TOKEN = "8038365883:AAHHr2yd1JUscRDnj-0jfBqOda8I5mz-eyU"
    bot = WordTranslatorBot(token=TOKEN)
    keep_alive() 
    bot.run()

