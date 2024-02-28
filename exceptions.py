class EndpointError(Exception):
    """Ошибка при возникновении проблем с запросом к эндпоинту."""

    pass


class ParseError(Exception):
    """Ошибка при ошибке парсинга статуса домашенй работы."""

    pass
