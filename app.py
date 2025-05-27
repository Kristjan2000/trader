from PIL import Image
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

image_path = r'C:\Users\Uporabnik\Downloads\111.jpeg'

img = Image.open(image_path)

text = pytesseract.image_to_string(img)

print("Extracted Text: ")
print(text)