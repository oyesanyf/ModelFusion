from PIL import Image

img = Image.open(r'd:\harfile\ModelFusion\reports\test_focus_screen.png')
crop = img.crop((550, 480, 800, 600))
crop.save(r'd:\harfile\ModelFusion\reports\crop_easy_apply.png')
print("Saved crop_easy_apply.png")
