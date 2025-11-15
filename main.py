import argparse
import sys
import tarfile
import io
import urllib.request
from urllib.parse import urlparse
from typing import Dict, List, Set, Tuple, Optional


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


def parse_apkindex(data: bytes) -> Dict[str, List[str]]:
    packages = {}
    current_pkg = {}
    current_name = None

    text = data.decode('utf-8', errors='ignore')
    lines = text.splitlines()

    for line in lines:
        line = line.strip()
        if not line:
            if current_name and 'P' in current_pkg:
                packages[current_name] = current_pkg.get('depends', [])
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
        packages[current_name] = current_pkg.get('depends', [])

    return packages


def load_apkindex_from_url(repo_url: str) -> Dict[str, List[str]]:
    index_url = f"{repo_url.rstrip('/')}/APKINDEX.tar.gz"
    try:
        print(f"Загрузка: {index_url}", file=sys.stderr)
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
        raise RuntimeError(f"Ошибка распаковки: {e}")


def load_apkindex_from_file(filepath: str) -> Dict[str, List[str]]:
    packages = {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split('->')
                if len(parts) != 2:
                    continue
                pkg = parts[0].strip()
                deps = [d.strip() for d in parts[1].split() if d.strip()]
                packages[pkg] = deps
        return packages
    except Exception as e:
        raise RuntimeError(f"Ошибка чтения файла: {e}")


def build_reverse_index(repo: Dict[str, List[str]]) -> Dict[str, List[str]]:
    reverse = {}
    for pkg, deps in repo.items():
        for dep in deps:
            reverse.setdefault(dep, []).append(pkg)
    return reverse


def build_dependency_graph(
    start_pkg: str,
    repo: Dict[str, List[str]],
    max_depth: int,
    filter_substr: str,
    visited: Optional[Set[str]] = None,
    path: Optional[Set[str]] = None,
    current_depth: int = 0,
    graph: Optional[Dict[str, List[str]]] = None,
) -> Tuple[Dict[str, List[str]], List[str]]:
    if visited is None:
        visited = set()
    if path is None:
        path = set()
    if graph is None:
        graph = {}

    if current_depth > max_depth:
        return graph, []

    if start_pkg in path:
        cycle = " -> ".join(list(path) + [start_pkg])
        return graph, [f"Цикл: {cycle}"]

    if filter_substr and filter_substr in start_pkg:
        return graph, []

    if start_pkg in visited:
        return graph, []

    deps = repo.get(start_pkg, [])
    filtered_deps = [d for d in deps if not (filter_substr and filter_substr in d)]
    graph[start_pkg] = filtered_deps
    visited.add(start_pkg)
    path.add(start_pkg)

    cycles: List[str] = []
    for dep in filtered_deps:
        sub_graph, sub_cycles = build_dependency_graph(
            dep, repo, max_depth, filter_substr,
            visited.copy(), path.copy(), current_depth + 1, graph
        )
        cycles.extend(sub_cycles)

    path.remove(start_pkg)
    return graph, cycles


def build_reverse_graph(
    start_pkg: str,
    reverse_repo: Dict[str, List[str]],
    max_depth: int,
    filter_substr: str,
    visited: Optional[Set[str]] = None,
    path: Optional[Set[str]] = None,
    current_depth: int = 0,
    graph: Optional[Dict[str, List[str]]] = None,
) -> Tuple[Dict[str, List[str]], List[str]]:
    if visited is None:
        visited = set()
    if path is None:
        path = set()
    if graph is None:
        graph = {}

    if current_depth > max_depth:
        return graph, []

    if start_pkg in path:
        cycle = " -> ".join(list(path) + [start_pkg])
        return graph, [f"Цикл: {cycle}"]

    if filter_substr and filter_substr in start_pkg:
        return graph, []

    if start_pkg in visited:
        return graph, []

    parents = reverse_repo.get(start_pkg, [])
    filtered_parents = [p for p in parents if not (filter_substr and filter_substr in p)]
    graph[start_pkg] = filtered_parents
    visited.add(start_pkg)
    path.add(start_pkg)

    cycles: List[str] = []
    for parent in filtered_parents:
        sub_graph, sub_cycles = build_reverse_graph(
            parent, reverse_repo, max_depth, filter_substr,
            visited.copy(), path.copy(), current_depth + 1, graph
        )
        cycles.extend(sub_cycles)

    path.remove(start_pkg)
    return graph, cycles


def _print_ascii_tree(
    node: str,
    graph: Dict[str, List[str]],
    visited: Set[str],
    prefix: str = "",
    is_last: bool = True,
    depth: int = 0,
    max_depth: int = 5,
) -> None:
    if depth > max_depth:
        return

    connector = "└── " if is_last else "├── "
    print(f"{prefix}{connector}{node}")

    children = graph.get(node, [])
    new_prefix = prefix + ("    " if is_last else "│   ")

    for i, child in enumerate(children):
        child_last = i == len(children) - 1
        if child in visited:
            ref = "└── " if child_last else "├── "
            print(f"{new_prefix}{ref}{child} (уже показан выше)")
            continue

        visited.add(child)
        _print_ascii_tree(
            child, graph, visited, new_prefix,
            child_last, depth + 1, max_depth
        )


def print_ascii_tree(graph: Dict[str, List[str]], start_pkg: str, max_depth: int):
    visited = set()
    print(start_pkg)
    if start_pkg in graph and graph[start_pkg]:
        visited.add(start_pkg)
        for i, child in enumerate(graph[start_pkg]):
            is_last = i == len(graph[start_pkg]) - 1
            _print_ascii_tree(
                child, graph, visited,
                prefix="", is_last=is_last,
                depth=1, max_depth=max_depth
            )
    else:
        print("  (нет зависимостей)")


def main():
    parser = argparse.ArgumentParser(
        description="Этап 4: Прямые и обратные зависимости",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument('--package', type=str, required=True, help='Имя пакета')
    parser.add_argument('--repo', type=validate_url, required=True, help='URL или путь')
    parser.add_argument('--test-mode', action='store_true', help='Тестовый режим')
    parser.add_argument('--reverse', action='store_true', help='Обратные зависимости')
    parser.add_argument('--ascii', action='store_true', help='ASCII-дерево')
    parser.add_argument('--max-depth', type=positive_int, default=5)
    parser.add_argument('--filter', type=str, default='')

    try:
        args = parser.parse_args()
    except argparse.ArgumentTypeError as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)

    if args.test_mode and not args.repo.startswith('./'):
        print("Ошибка: --test-mode требует локальный путь", file=sys.stderr)
        sys.exit(1)

    print("Конфигурация:")
    print(f"package={args.package}")
    print(f"repo={args.repo}")
    print(f"test_mode={args.test_mode}")
    print(f"reverse={args.reverse}")
    print(f"ascii={args.ascii}")
    print(f"max_depth={args.max_depth}")
    print(f"filter={args.filter!r}")
    print()

    try:
        repo = load_apkindex_from_file(args.repo) if args.test_mode else load_apkindex_from_url(args.repo)
        print(f"Репозиторий загружен: {len(repo)} пакетов", file=sys.stderr)

        if args.package not in repo and not args.reverse:
            print(f"Пакет '{args.package}' не найден", file=sys.stderr)
            sys.exit(1)

        reverse_repo = build_reverse_index(repo)

        if args.reverse:
            if args.package not in reverse_repo:
                print(f"Никто не зависит от '{args.package}'")
                return
            graph, cycles = build_reverse_graph(
                args.package, reverse_repo, args.max_depth, args.filter
            )
            title = f"Пакеты, зависящие от '{args.package}'"
        else:
            graph, cycles = build_dependency_graph(
                args.package, repo, args.max_depth, args.filter
            )
            title = f"Зависимости пакета '{args.package}'"

        if cycles:
            print("Обнаружены циклы:")
            for c in set(cycles):
                print(f"  {c}")
            print()

        if args.ascii:
            print(f"{title} (глубина ≤ {args.max_depth}):")
            print_ascii_tree(graph, args.package, args.max_depth)
        else:
            print(f"{title} построены. Используйте --ascii для просмотра.")

    except Exception as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)

    print("\nЭтап 4 завершён успешно.")


if __name__ == '__main__':
    main()