import sys
import json
from core.text_extractor import extract_text_from_file
from core.information_parser import parse_resume

def main():
    if len(sys.argv) < 2:
        print("Usage: python run_parser.py <path_to_resume_file>")
        print("Example: python run_parser.py sample_resumes/my_resume.pdf")
        sys.exit(1)

    file_path = sys.argv[1]

    try:
        print(f"Extracting text from: {file_path}")
        raw_text = extract_text_from_file(file_path)
        # print("\n--- Raw Extracted Text (first 1000 chars) ---")
        # print(raw_text[:1000] + "..." if len(raw_text) > 1000 else raw_text)

        print("\n--- Parsing Information ---")
        parsed_data = parse_resume(raw_text)

        print("\n--- Structured JSON Output ---")
        print(json.dumps(parsed_data, indent=2))

    except FileNotFoundError:
        print(f"Error: File not found at '{file_path}'")
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()