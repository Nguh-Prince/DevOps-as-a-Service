import re

def slugify(string):
    slug = string.lower()
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = slug.strip('-')

    return slug