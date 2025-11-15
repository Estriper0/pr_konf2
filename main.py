import argparse
import sys
from urllib.parse import urlparse


def validate_url(url: str) -> str:
    if url.startswith('/'):  # локальный путь
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


def main():
    parser = argparse.ArgumentParser(
        description="Инструмент визуализации графа зависимостей (Этап 1)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        '--package',
        type=str,
        required=True,
        help='Имя анализируемого пакета'
    )
    parser.add_argument(
        '--repo',
        type=validate_url,
        required=True,
        help='URL репозитория или путь к тестовому файлу'
    )

    # Необязательные
    parser.add_argument(
        '--test-mode',
        action='store_true',
        help='Режим работы с тестовым репозиторием'
    )
    parser.add_argument(
        '--ascii',
        action='store_true',
        help='Вывод зависимостей в формате ASCII-дерева'
    )
    parser.add_argument(
        '--max-depth',
        type=positive_int,
        default=5,
        help='Максимальная глубина анализа зависимостей (по умолчанию: 5)'
    )
    parser.add_argument(
        '--filter',
        type=str,
        default='',
        help='Подстрока для фильтрации пакетов (исключение)'
    )

    try:
        args = parser.parse_args()
    except argparse.ArgumentTypeError as e:
        print(f"Ошибка валидации параметра: {e}", file=sys.stderr)
        sys.exit(1)
    except SystemExit:
        sys.exit(1)

    if args.test_mode and not args.repo.startswith('/'):
        print("Ошибка: в режиме --test-mode репозиторий должен быть локальным файлом (абсолютный или относительный путь)", file=sys.stderr)
        sys.exit(1)

    if args.filter and len(args.filter) < 2:
        print("Предупреждение: фильтр слишком короткий, будет проигнорирован", file=sys.stderr)
        args.filter = ''

    print("Конфигурация приложения:")
    print(f"package={' '.join(args.package.split())}")
    print(f"repo={args.repo}")
    print(f"test_mode={args.test_mode}")
    print(f"ascii={args.ascii}")
    print(f"max_depth={args.max_depth}")
    print(f"filter={args.filter!r}")

if __name__ == '__main__':
    main()