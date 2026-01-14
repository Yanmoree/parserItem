import os
import sys

def export_project(root_dir='.', output_file='project_export.txt'):
    """Экспортирует структуру и содержимое файлов проекта"""
    
    # Игнорируемые папки и файлы
    IGNORE_DIRS = {'.git', '__pycache__', 'node_modules', 'venv', 'env', '.idea', '.vscode'}
    IGNORE_EXT = {'.pyc', '.pyo', '.so', '.dll', '.exe', '.bin', '.jpg', '.png', '.pdf'}
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for root, dirs, files in os.walk(root_dir):
            # Исключаем игнорируемые директории
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, root_dir)
                
                # Пропускаем игнорируемые расширения
                if any(file.endswith(ext) for ext in IGNORE_EXT):
                    continue
                
                # Пропускаем слишком большие файлы (> 1MB)
                try:
                    if os.path.getsize(file_path) > 1024 * 1024:
                        f.write(f"\n=== Файл: {rel_path} (пропущен - слишком большой) ===\n\n")
                        continue
                except:
                    pass
                
                f.write(f"\n{'='*60}\n")
                f.write(f"ФАЙЛ: {rel_path}\n")
                f.write(f"{'='*60}\n\n")
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as content_file:
                        content = content_file.read()
                        f.write(content)
                except Exception as e:
                    f.write(f"[Ошибка чтения файла: {e}]\n")
                
                f.write("\n" + "="*60 + "\n")
    
    print(f"Проект экспортирован в файл: {output_file}")

if __name__ == "__main__":
    # Использовать текущую директорию или указанную
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    output = sys.argv[2] if len(sys.argv) > 2 else 'project_export.txt'
    export_project(root, output)