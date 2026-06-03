# AdaIN Style Transfer Web Service

Веб-сервис для переноса художественного стиля на изображения. Разработан в рамках выпускной квалификационной работы.

Используемые технологии: FastAPI, Pytorch + HTML/JS/CSS
Архитектура модели (net.py, function.py) и предобученные веса (decoder.pth, vgg_normalised.pth) взяты из репозитория [pytorch-AdaIN](https://github.com/naoto0804/pytorch-AdaIN).

Запуск приложения: uvicorn app:app --host 0.0.0.0 --port 8000
