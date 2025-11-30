import os
import fnmatch

# 1. Dossiers visibles mais dont on cache le contenu
HIDE_CONTENT = {
    ".git/objects",
     ".git/refs",
    ".git/hooks",
     ".git/logs",
      ".git",
}

# 2. Dossiers complètement ignorés
IGNORE_DIRS = {
    "__pycache__",
    "moi"
}

# 3. Patterns de fichiers ignorés
IGNORE_PATTERNS = [
    "*.pyc",
    "*_moi.py"
]

def normalize(path):
    return path.replace("\\", "/").rstrip("/")

def is_hidden_content_dir(path):
    n = normalize(path)
    return any(n.endswith(h) for h in HIDE_CONTENT)

def is_ignored_dir(path):
    name = os.path.basename(path)
    return name in IGNORE_DIRS

def is_ignored_file(name):
    return any(fnmatch.fnmatch(name, pat) for pat in IGNORE_PATTERNS)

def print_tree(path, prefix=""):
    try:
        entries = sorted(os.listdir(path))
    except PermissionError:
        return

    # Filtrage
    filtered = []
    for name in entries:
        full = os.path.join(path, name)
        if os.path.isdir(full):
            if is_ignored_dir(full):
                continue
        else:
            if is_ignored_file(name):
                continue
        filtered.append(name)

    for i, name in enumerate(filtered):
        full = os.path.join(path, name)
        connector = "└── " if i == len(filtered)-1 else "├── "
        print(prefix + connector + name)

        if os.path.isdir(full):
            # on ne descend pas dans le contenu des dossiers HIDE_CONTENT
            if is_hidden_content_dir(full):
                continue

            new_prefix = prefix + ("    " if i == len(filtered)-1 else "│   ")
            print_tree(full, new_prefix)

# Point de départ
print_tree(".")


import os
import fnmatch



def normalize(path):
    return path.replace("\\", "/").rstrip("/")


def is_hidden_content_dir(path):
    n = normalize(path)
    return any(n.endswith(h) for h in HIDE_CONTENT)


def is_ignored_dir(path):
    name = os.path.basename(path)
    return name in IGNORE_DIRS


def is_ignored_file(name):
    return any(fnmatch.fnmatch(name, pat) for pat in IGNORE_PATTERNS)


def build_tree_md(path, indent=""):
    lines = []

    try:
        entries = sorted(os.listdir(path))
    except PermissionError:
        return []

    # Filtrer
    filtered = []
    for name in entries:
        full = os.path.join(path, name)
        if os.path.isdir(full) and is_ignored_dir(full):
            continue
        if os.path.isfile(full) and is_ignored_file(name):
            continue
        filtered.append(name)

    # Construire le markdown
    for name in filtered:
        full = os.path.join(path, name)
        prefix = indent + "- "

        # Indiquer les dossiers avec "/"
        if os.path.isdir(full):
            lines.append(f"{prefix}{name}/")

            # Ne pas descendre dans certains dossiers
            if is_hidden_content_dir(full):
                continue

            lines.extend(build_tree_md(full, indent + "  "))
        else:
            lines.append(f"{prefix}{name}")

    return lines


# Génère l'arbre markdown depuis le dossier courant
markdown_tree = "\n".join(build_tree_md("."))

# Affiche la sortie Markdown
print(markdown_tree)

# Si tu veux l'enregistrer dans un fichier :
with open("arborescence.md", "w") as f:
   f.write(markdown_tree)