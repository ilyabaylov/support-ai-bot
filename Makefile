.PHONY: install index run test

# установить зависимости
install:
	pip install -r requirements.txt

# собрать векторный индекс из базы знаний
index:
	python -m scripts.build_index

# запустить бота
run:
	python -m app.bot

# прогнать тесты
test:
	pytest -q
