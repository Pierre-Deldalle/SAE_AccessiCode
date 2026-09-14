from bs4 import BeautifulSoup

def extract_images_and_context(html_content: str) -> list:
    soup = BeautifulSoup(html_content, 'html.parser')
    images = soup.find_all('img')
    extracted = []

    for idx, img in enumerate(images):
        extracted.append({
            "image_id": f"img_{idx+1}",
            "src": img.get('src', ''),
            "alt": img.get('alt', ''),
            "title": img.get('title', ''),
            "aria-label": img.get('aria-label', ''),
            "role": img.get('role', ''),
            "parent_tag": img.parent.name if img.parent else 'body'
        })

    return extracted