from pathlib import Path
import win32com.client as win32
from docxtpl import DocxTemplate


def convert_docx_to_pdf(template_path, context, output_doc_path):
    """
    Функция для рендеринга шаблона DOCX с контекстом, сохранения в DOCX и конвертации в PDF.

    :param template_path: Путь к шаблону DOCX.
    :param context: Контекст для заполнения шаблона.
    :param output_doc_path: Путь для сохранения сгенерированного файла.

    :return: Путь к созданному PDF файлу.
    """

    base_dir = Path("data").resolve()  # Абсолютный путь к data

    template_doc_path = (base_dir / template_path).with_suffix(".docx").resolve()
    output_docx_path = (base_dir / output_doc_path).with_suffix(".docx").resolve()
    output_pdf_path = (base_dir / output_doc_path).with_suffix(".pdf").resolve()

    # Render & Save Word Document
    doc = DocxTemplate(template_doc_path)
    doc.render(context)
    doc.save(output_docx_path)

    word = win32.DispatchEx("Word.Application")
    worddoc = word.Documents.Open(str(output_docx_path))
    worddoc.SaveAs(str(output_pdf_path), FileFormat=17)
    worddoc.Close()
    word.NormalTemplate.Saved = True
    word.Quit()
    del word

    # Delete the original DOCX file after conversion
    if output_docx_path.exists():
        output_docx_path.unlink()

    # Return the PDF file path
    return output_pdf_path
