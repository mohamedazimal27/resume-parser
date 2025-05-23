import fitz 
from docx import Document
from io import BytesIO

def extract_text_from_pdf(file_content: bytes) -> str:
    """Extracts text from PDF file content."""
    text = ""
    try:
        doc = fitz.open(stream=file_content, filetype="pdf")
        for page in doc:
            text += page.get_text()
        doc.close()
    except Exception as e:
        print(f"Error extracting PDF text: {e}")
        raise
    return text

def extract_text_from_docx(file_content: bytes) -> str:
    """Extracts text from DOCX file content."""
    text = []
    try:
        doc = Document(BytesIO(file_content))
        for para in doc.paragraphs:
            text.append(para.text)
    except Exception as e:
        print(f"Error extracting DOCX text: {e}")
        raise
    return "\n".join(text)

def extract_text_from_file(file_path: str) -> str:
    """Reads a file from path and extracts text based on file type."""
    with open(file_path, "rb") as f:
        file_content = f.read()

    if file_path.lower().endswith(".pdf"):
        return extract_text_from_pdf(file_content)
    elif file_path.lower().endswith(".docx"):
        return extract_text_from_docx(file_content)
    else:
        raise ValueError("Unsupported file type. Only .pdf and .docx are supported.")

# Example usage (for testing this module independently)
if __name__ == "__main__":
    # Create dummy files for testing
    with open("dummy.pdf", "w") as f: f.write("This is a dummy PDF content.") # Not real PDF, just for placeholder
    with open("dummy.docx", "w") as f: f.write("This is a dummy DOCX content.") # Not real DOCX, just for placeholder

    try:
        # Replace with actual file paths for real testing
        pdf_text = extract_text_from_file("path/to/your/resume.pdf")
        print("PDF Text (partial):", pdf_text[:500])
        docx_text = extract_text_from_file("path/to/your/resume.docx")
        print("DOCX Text (partial):", docx_text[:500])
    except FileNotFoundError:
        print("Please place actual resume files in 'path/to/your/resume.pdf' etc. for testing.")
    finally:
        import os
        # os.remove("dummy.pdf") # Uncomment to clean up dummy files
        # os.remove("dummy.docx")