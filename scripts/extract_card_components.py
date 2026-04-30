import os

from PIL import Image


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    card_dir = os.path.join(base_dir, "data", "card")
    comp_dir = os.path.join(card_dir, "components")

    os.makedirs(comp_dir, exist_ok=True)

    # 1. Base Card
    # Let's create a base card by opening S_2, and overwriting the inside with white
    # while preserving the border and rounded corners.
    s2_path = os.path.join(card_dir, "S_2.png")
    if os.path.exists(s2_path):
        base_img = Image.open(s2_path).convert("RGBA")
        # Overwrite the text and suits areas with white (or the background color)
        # assuming background is mostly white at pixel (20,50)
        bg_color = (255, 255, 255, 255)
        # We can just fill a rect
        # Erase top-left text
        for x in range(10, 65):
            for y in range(5, 45):
                base_img.putpixel((x, y), bg_color)
        # Erase bottom-right text
        for x in range(84, 140):
            for y in range(173, 215):
                base_img.putpixel((x, y), bg_color)
        # Erase center suit
        for x in range(38, 115):
            for y in range(78, 155):
                base_img.putpixel((x, y), bg_color)
        base_img.save(os.path.join(comp_dir, "base_card.png"))
        print("Generated base_card.png")

    # 2. Extract Suit Icons from Aces
    suits = {"S": "S_A.png", "H": "H_A.png", "D": "D_A.png", "C": "C_A.png"}
    # The center of the ace usually contains the big suit.
    # Dimensions: 150x220. Center is ~ 75, 110. Let's crop 40x40 to 110x180.
    # Actually let's crop 40, 70, 110, 150
    suit_box = (35, 65, 115, 155)
    for s_name, s_file in suits.items():
        path = os.path.join(card_dir, s_file)
        if os.path.exists(path):
            img = Image.open(path).convert("RGBA")
            suit_img = img.crop(suit_box)
            suit_img.save(os.path.join(comp_dir, f"suit_{s_name}.png"))
            print(f"Generated suit_{s_name}.png")

    # 3. Extract Text Masks from Spades (A, 2-10, J, Q, K)
    # The rank text + small suit is usually at the top left.
    # Let's crop the top left: 5, 5, 40, 70
    ranks = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
    text_box = (10, 5, 65, 45)
    for rank in ranks:
        path = os.path.join(card_dir, f"S_{rank}.png")
        if os.path.exists(path):
            img = Image.open(path).convert("RGBA")
            text_img = img.crop(text_box)
            # Make the background transparent. We know the text is black.
            pixels = text_img.load()
            w, h = text_img.size
            for x in range(w):
                for y in range(h):
                    r, g, b, a = pixels[x, y]
                    # If it's not dark, make it transparent
                    if r > 100 or g > 100 or b > 100:
                        pixels[x, y] = (0, 0, 0, 0)
                    else:
                        # Make the black text into a white mask so we can colorize it later
                        # OR just keep it black, and we can colorize it by changing pixels
                        pass

            text_img.save(os.path.join(comp_dir, f"text_{rank}.png"))
            print(f"Generated text_{rank}.png")


if __name__ == "__main__":
    main()
