import sys
from PIL import Image


def stack_vertically(img_paths):
    imgs = [Image.open(path) for path in img_paths]
    stacked_width = max(img.width for img in imgs)
    padding = 1
    stacked_height = sum(img.height for img in imgs) + padding * (len(imgs) - 1)
    stacked_img = Image.new("RGB", (stacked_width, stacked_height), (208, 215, 222))
    yedge = 0
    for img in imgs:
        stacked_img.paste(img, (0, yedge))
        yedge += img.height + padding
    return stacked_img


if __name__ == "__main__":
    stack_vertically(sys.argv[1:]).save("stacked.png")
