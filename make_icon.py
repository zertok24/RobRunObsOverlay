from PIL import Image

img = Image.open("logo.png").convert("RGBA")
side = max(img.size)
square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
square.paste(img, ((side - img.width) // 2, (side - img.height) // 2))
square.save("icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
