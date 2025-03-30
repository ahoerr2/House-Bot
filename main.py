import io
import os
import textwrap

import discord
from discord.ext import commands
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

TOKEN_ENVIROMENT_NAME = "DISCORD_TOKEN"

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

load_dotenv(verbose=False)

TOKEN = os.getenv(TOKEN_ENVIROMENT_NAME)

if not TOKEN:
    raise EnvironmentError(
        f"Failed to get evironment variable from env {TOKEN_ENVIROMENT_NAME}"
    )


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await bot.tree.sync()
    print("Slash commands synced")


@bot.hybrid_command(name="hello", description="A simple hello command")
async def hello(ctx: commands.Context):
    await ctx.send(f"Hey great day in our house {ctx.author.display_name}!")


def create_titlecard(
    text,
    background_path="sbob_background.webp",
    font_path="spongeboy.ttf",
    line_spacing_factor=1.1,
):
    """
    Generate a titlecard with text centered on the background image.
    Text will be dynamically resized and wrapped based on content.

    Args:
        text (str): The text to display on the titlecard
        background_path (str): Path to the background image
        font_path (str): Path to the font file
        line_spacing_factor (float): Factor to multiply line height by for spacing (1.0 = no extra space)

    Returns:
        io.BytesIO: Image as a BytesIO object for sending via discord.py
    """
    # Open the background image
    try:
        background = Image.open(background_path).convert("RGBA")
    except FileNotFoundError:
        print(f"Background image '{background_path}' not found.")
        return None

    # Get image dimensions
    img_width, img_height = background.size

    # Create a drawing context
    draw = ImageDraw.Draw(background)

    # Calculate the maximum width for text (80% of image width)
    max_text_width = int(img_width * 0.8)

    # Start with a large font size and decrease until text fits
    font_size = int(img_height / 4)  # Start with 1/4 of image height
    min_font_size = 20  # Minimum readable font size

    # Function to wrap text by words
    def word_wrap(text, font, max_width):
        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            # Check if adding this word would exceed the max width
            test_line = current_line + " " + word if current_line else word
            bbox = draw.textbbox((0, 0), test_line, font=font)
            line_width = bbox[2] - bbox[0]

            if line_width <= max_width:
                # Word fits, add it to the current line
                current_line = test_line
            else:
                # Word doesn't fit, start a new line
                if current_line:
                    lines.append(current_line)

                # Check if the word alone fits on a line
                bbox = draw.textbbox((0, 0), word, font=font)
                word_width = bbox[2] - bbox[0]

                if word_width <= max_width:
                    # Word fits on its own line
                    current_line = word
                else:
                    # Word is too long even on its own line
                    # We'll continue reducing font size
                    return None

        # Add the last line if it's not empty
        if current_line:
            lines.append(current_line)

        return lines

    # Find the appropriate font size and wrap text
    font = None
    wrapped_text = None

    while font_size >= min_font_size:
        try:
            font = ImageFont.truetype(font_path, font_size)

            # Try to wrap text with current font size
            wrapped_text = word_wrap(text, font, max_text_width)

            # If word_wrap returned None, a word was too long for the line
            if wrapped_text is None:
                # Reduce font size and try again
                font_size -= 5
                continue

            # Calculate line height with a test string that includes tall characters
            test_text = "TygpqjÁÇÊ"  # Text with various ascenders and descenders
            bbox = draw.textbbox((0, 0), test_text, font=font)
            line_height = bbox[3] - bbox[1]

            # Apply line spacing factor
            spaced_line_height = int(line_height * line_spacing_factor)

            # Calculate total text height with spacing
            total_height = spaced_line_height * len(wrapped_text)

            # Check if text fits in 80% of image height
            if total_height <= img_height * 0.8:
                break
        except Exception as e:
            print(f"Error with font size {font_size}: {e}")

        # Reduce font size and try again
        font_size -= 5

    if font_size < min_font_size:
        print("Warning: Text may be too small to read clearly.")
        font_size = min_font_size
        font = ImageFont.truetype(font_path, font_size)

        # One final attempt at wrapping with minimum font size
        wrapped_text = word_wrap(text, font, max_text_width)

        # If still not possible, use a simple fallback approach
        if wrapped_text is None:
            # Split into shorter segments as a last resort
            words = text.split()
            wrapped_text = []

            current_line = ""
            for word in words:
                if current_line:
                    current_line += " " + word
                else:
                    current_line = word

                # Check line length periodically
                if len(current_line.split()) >= 3:
                    wrapped_text.append(current_line)
                    current_line = ""

            # Add any remaining text
            if current_line:
                wrapped_text.append(current_line)

        # Recalculate line height for minimum font size
        test_text = "TygpqjÁÇÊ"
        bbox = draw.textbbox((0, 0), test_text, font=font)
        line_height = bbox[3] - bbox[1]
        spaced_line_height = int(line_height * line_spacing_factor)

    # Calculate total text height for centering (with spacing)
    total_height = spaced_line_height * len(wrapped_text)

    # Calculate starting y position to center text vertically
    y_position = (img_height - total_height) // 2

    # Draw each line of text
    for line in wrapped_text:
        # Calculate line width for horizontal centering
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        x_position = (img_width - line_width) // 2

        # Draw the main text
        draw.text((x_position, y_position), line, font=font, fill="#f9e801")

        # Update y position for next line using consistent line height with spacing
        y_position += spaced_line_height

    # Create a fresh BytesIO object
    byte_io = io.BytesIO()

    # Save the image to the BytesIO object with explicit format
    background.save(byte_io, format="PNG")

    # Reset the pointer to the beginning of the BytesIO object
    byte_io.seek(0)

    # Return the BytesIO object
    return byte_io


ACTIVITY_OPTIONS = [
    "goes to the mall",
    "goes to cedar point",
    "helps at the animal shelter",
    "look at cool smiley",
    "go to game night",
]


# Autocomplete function for activity parameter
async def activity_autocomplete(
    interaction: discord.Interaction, current: str
) -> list[discord.app_commands.Choice[str]]:
    # Filter options based on what the user has typed so far
    return [
        discord.app_commands.Choice(name=option, value=option)
        for option in ACTIVITY_OPTIONS
        if current.lower() in option.lower()
    ][:25]  # Discord limits to 25 choices


@bot.hybrid_command(name="image", description="Sends an image with custom text")
@discord.app_commands.autocomplete(activity=activity_autocomplete)
async def send_image(
    ctx: commands.Context,
    activity: str = commands.parameter(description="Activity for housers to do"),
):
    title_card = create_titlecard(f"{activity}")
    if title_card:
        await ctx.send(file=discord.File(fp=title_card, filename="titlecard.png"))
        return

    await ctx.send(content="Failure to create titlecard")


bot.run(TOKEN)
