import logging
import re

logger = logging.getLogger(__name__)


def extract_text(filename: str, file_bytes: bytes) -> str:
    """Extract text from various file formats"""
    logger.info(f"Extracting text from: {filename}")

    filename = (filename or "").lower()

    try:
        if filename.endswith(".pdf"):
            return extract_from_pdf(file_bytes)
        elif filename.endswith(".txt") or filename.endswith(".csv"):
            return extract_from_text(file_bytes)
        elif filename.endswith((".xlsx", ".xls")):
            return extract_from_excel(file_bytes, filename)
        else:
            raise ValueError(f"Unsupported file type: {filename}")
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Error extracting text: {str(e)}")
        raise


def extract_from_text(file_bytes: bytes) -> str:
    """Extract from TXT/CSV file"""
    logger.info("Extracting from text file")
    try:
        text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = file_bytes.decode("latin-1")
    return text.strip()


def extract_from_pdf(file_bytes: bytes) -> str:
    """Extract from PDF file"""
    logger.info("Extracting from PDF file")
    from pypdf import PdfReader
    from io import BytesIO

    try:
        pdf = PdfReader(BytesIO(file_bytes))
        text = ""

        for page_num in range(len(pdf.pages)):
            page = pdf.pages[page_num]
            text += page.extract_text()
            text += "\n"

        logger.info(f"Extracted {len(text)} characters from PDF")
        return text.strip()
    except Exception as e:
        logger.error(f"PDF extraction failed: {str(e)}")
        raise ValueError("Failed to extract text from PDF")


def extract_from_excel(file_bytes: bytes, filename: str) -> str:
    """Extract from XLSX/XLS file"""
    logger.info("Extracting from Excel file")
    from openpyxl import load_workbook
    from io import BytesIO

    try:
        workbook = load_workbook(BytesIO(file_bytes), read_only=True)
        text = ""

        for sheet_name in workbook.sheetnames:
            sheet = workbook[sheet_name]
            text += f"\n=== {sheet_name} ===\n"

            for row in sheet.iter_rows(values_only=True):
                for cell in row:
                    if cell is not None:
                        text += f"{cell} | "
                text += "\n"

        logger.info(f"Extracted {len(text)} characters from Excel")
        return text.strip()
    except Exception as e:
        logger.error(f"Excel extraction failed: {str(e)}")
        raise ValueError("Failed to extract text from Excel file")


def clean_and_chunk(text: str, chunk_size: int = 2000) -> str:
    """Clean text and prepare for LLM"""
    logger.info(f"Cleaning and chunking text ({len(text)} chars)")

    # Normalize all whitespace to single spaces
    text = re.sub(r"\s+", " ", text)

    # Strip control characters but keep normal punctuation and non-ASCII
    # (Hindi/Gujarati business info must survive cleaning)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # Remove URLs
    text = re.sub(r"http[s]?://\S+", "", text)

    # Remove email addresses
    text = re.sub(r"\S+@\S+", "", text)

    text = text.strip()

    logger.info(f"Cleaned text to {len(text)} characters")

    return text
