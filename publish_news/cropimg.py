from PIL import Image
def tailer(fp,box):
# fp = r'C:\Users\Administrator\Desktop\test\images\1.png'
    raw_im = Image.open(fp)
    cropim = raw_im.crop(box)
    return cropim

