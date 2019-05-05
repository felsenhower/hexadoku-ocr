# hexadoku-ocr

A ~bash~ Python script that uses ImageMagick and Tesseract to recognize the content of Hexadokus given as image files and writes them to a LaTeX file.

### Dependencies

* **Python 3**
* **ImageMagick** (`convert`, `identify`) is used to preprocess the images for OCR
* **Tesseract** is used for OCR

### Usage
`./read_hexadoku.py samples/sample_riddle.png samples/sample_solution.png test_{riddle,solution}.tex`
