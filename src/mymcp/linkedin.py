
import re
import tempfile
import subprocess
from markdownify import markdownify

def get_html_with_chromium(url: str, in_markdown: bool = True, user_data_dir:str = None) -> str:
    """
    Uses Chromium in headless mode to fetch the HTML of the given URL.
    
    Parameters:
    - url (str): The URL to fetch.

    Returns:
    - str: The HTML content of the page.
    """
    with tempfile.NamedTemporaryFile(mode='r+', delete=True) as tmp_file:
        try:
            subprocess.run(
                [
                    "chromium",
                    #"--headless",
                    f"--user-data-dir={user_data_dir}" if user_data_dir else "",
                    "--disable-gpu",
                    "--dump-dom",
                    url,
                ],
                stdout=tmp_file,
                stderr=subprocess.PIPE,
                check=True
            )
            tmp_file.seek(0)
            
            html_content = tmp_file.read()
            
            if in_markdown:
                return markdownify(html_content)
            
            return html_content
        
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Chromium failed: {e.stderr.decode().strip()}")

def retrieve_jobs_linkedin(url):
    
    html_code = get_html_with_chromium(url)
    #urls = retrieve_jobs_linkedin(html_code)

    pattern = r'/jobs/view/[^/]*(\d{10})'
    ids = re.findall(pattern, html_code)
    
    return [ f"https://www.linkedin.com/jobs/view/{id}/" for id in ids ]

def extract_linkedin_ofuscated_job_opening(input_text):
    """
    Extracts all instances of "text":"<text to extract>" from input text.
    
    Args:
        input_text (str): The text to search through
        
    Returns:
        list: A list of all extracted text values (without the "text":" wrapper)
    """
    # Regular expression pattern to match "text":"<content>"
    pattern = r'"text":"(.*?)"'
    
    # Find all matches in the input text
    matches = re.findall(pattern, input_text)
    
    return "\n".join(matches).encode().decode('unicode_escape')

def extract_linkedin_job_description(url):
    description:str = get_html_with_chromium(url, in_markdown=False)

    if unofuscated_description:= extract_linkedin_ofuscated_job_opening(description):
        description = unofuscated_description

    return description
