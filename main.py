import argparse
import sys
import tarfile
import io
import urllib.request
from urllib.parse import urlparse
from typing import Dict, List, Optional


def validate_url(url: str) -> str:
    if url.startswith('./'):
        return url
    try:
        result = urlparse(url)
        if result.scheme in ('http', 'https') and result.netloc:
            return url
        raise ValueError("URL должен содержать схему (http/https) и домен")
    except Exception as e:
        raise argparse.ArgumentTypeError(f"Некорректный URL или путь: {e}")


def positive_int(value: str) -> int:
    try:
        ivalue = int(value)
        if ivalue <= 0:
            raise ValueError("Число должно быть положительным")
        return ivalue
    except ValueError:
        raise argparse.ArgumentTypeError("Максимальная глубина должна быть положительным целым числом")


def parse_apkindex(data: bytes) -> Dict[str, Dict[str, str]]:
    packages = {}
    current_pkg = {}
    current_name = None

    text = data.decode('utf-8', errors='ignore')
    lines = text.splitlines()

    for line in lines:
        line = line.strip()
        if not line:
            if current_name and 'P' in current_pkg:
                packages[current_name] = current_pkg
            current_pkg = {}
            current_name = None
            continue

        if ':' not in line:
            continue
        key, value = line.split(':', 1)
        value = value.strip()

        if key == 'P':
            current_name = value
            current_pkg = {'P': value}
        elif key == 'D':
            deps = []
            for dep in value.split():
                clean_dep = dep.split(':', 1)[-1] if ':' in dep else dep
                clean_dep = clean_dep.split('=')[0]
                if clean_dep and clean_dep != current_name:
                    deps.append(clean_dep)
            current_pkg['depends'] = deps
        else:
            current_pkg[key] = value

    if current_name and 'P' in current_pkg:
        packages[current_name] = current_pkg

    return packages


def load_apkindex_from_url(repo_url: str) -> Dict[str, Dict[str, str]]:
    index_url = f"{repo_url.rstrip('/')}/APKINDEX.tar.gz"
    try:
        print(f"Загрузка индекса: {index_url}", file=sys.stderr)
        with urllib.request.urlopen(index_url, timeout=10) as response:
            data = response.read()
    except Exception as e:
        raise RuntimeError(f"Не удалось загрузить APKINDEX: {e}")

    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            for member in tar.getmembers():
                if member.name == "APKINDEX":
                    apkindex_data = tar.extractfile(member).read()
                    return parse_apkindex(apkindex_data)
            raise RuntimeError("APKINDEX не найден в архиве")
    except Exception as e:
        raise RuntimeError(f"Ошибка распаковки APKINDEX.tar.gz: {e}")


def load_apkindex_from_file(filepath: str) -> Dict[str, Dict[str, str]]:
    packages = {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                # Формат: A -> B C D
                parts = line.split('->')
                if len(parts) != 2:
                    continue
                pkg = parts[0].strip()
                deps = [d.strip() for d in parts[1].split() if d.strip()]
                packages[pkg] = {'P': pkg, 'depends': deps}
        return packages
    except Exception as e:
        raise RuntimeError(f"Ошибка чтения тестового файла: {e}")


def get_direct_dependencies(package_name: str, repo_data: Dict[str, Dict]) -> List[str]:
    pkg = repo_data.get(package_name)
    if not pkg:
        raise ValueError(f"Пакет '{package_name}' не найден в репозитории")
    return pkg.get('depends', [])


def main():
    parser = argparse.ArgumentParser(
        description="Этап 2: Сбор прямых зависимостей из APKINDEX",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument('--package', type=str, required=True, help='Имя пакета')
    parser.add_argument('--repo', type=validate_url, required=True, help='URL репозитория или путь к файлу')
    parser.add_argument('--test-mode', action='store_true', help='Тестовый режим (локальный файл)')
    parser.add_argument('--ascii', action='store_true')
    parser.add_argument('--max-depth', type=positive_int, default=5)
    parser.add_argument('--filter', type=str, default='')

    try:
        args = parser.parse_args()
    except argparse.ArgumentTypeError as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)

    if args.test_mode and not args.repo.startswith('./'):
        print("Ошибка: --test-mode требует локальный путь к файлу", file=sys.stderr)
        sys.exit(1)

    print("Конфигурация:")
    print(f"package={args.package}")
    print(f"repo={args.repo}")
    print(f"test_mode={args.test_mode}")
    print(f"ascii={args.ascii}")
    print(f"max_depth={args.max_depth}")
    print(f"filter={args.filter!r}")
    print()

    try:
        if args.test_mode:
            repo_data = load_apkindex_from_file(args.repo)
            print(f"Тестовый репозиторий загружен: {len(repo_data)} пакетов", file=sys.stderr)
        else:
            repo_data = load_apkindex_from_url(args.repo)
            print(f"Репозиторий загружен: {len(repo_data)} пакетов", file=sys.stderr)

        deps = get_direct_dependencies(args.package, repo_data)

        if not deps:
            print(f"Пакет '{args.package}' не имеет прямых зависимостей.")
        else:
            print("Прямые зависимости:")
            for dep in sorted(deps):
                print(f"  - {dep}")

    except Exception as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()