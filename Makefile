test_1:
	python main.py --package A --repo ./test_repo_1.txt --test-mode --ascii --mermaid

test_2:
	python main.py --package Web --repo ./test_repo_2.txt --test-mode --ascii --mermaid

test_nginx:
	python main.py --package nginx --repo https://dl-cdn.alpinelinux.org/alpine/v3.19/main/x86_64 --ascii --mermaid

test_busybox:
	python main.py --package busybox --repo https://dl-cdn.alpinelinux.org/alpine/v3.19/main/x86_64 --ascii --mermaid

test_python3:
	python main.py --package python3 --repo https://dl-cdn.alpinelinux.org/alpine/v3.19/main/x86_64 --ascii --mermaid